import logging
import os
import urllib.parse
from concurrent.futures.thread import ThreadPoolExecutor

import lol_dto
import riot_transmute
import riotwatcher
from lol_dto.classes.game import LolGame

from lol_esports_parser.dto.series_dto import LolSeries, create_series
from lol_esports_parser.parsers.riot.acs_access import ACS


acs = ACS()
lol_watcher = riotwatcher.LolWatcher(os.environ["RIOT_API_KEY"])


def get_riot_series(mh_url_list: list, get_timeline: bool = False, add_names: bool = True) -> LolSeries:
    """Gets a list of Riot API games as a single LolSeries object.

    Params:
        mh_url_list: the list of match history URLs to include in the series object.
        get_timeline: whether or not to query the /timeline/ endpoints for the games.
        add_names: whether or not to add champions/items/runes names next to their objects through lol_id_tools.

    Returns:
        A LolSeries made from all the games in the given order.
    """
    games_futures = []
    with ThreadPoolExecutor() as executor:
        for mh_url in mh_url_list:
            games_futures.append(executor.submit(get_riot_game, mh_url, get_timeline, add_names))

    return create_series([g.result() for g in games_futures])


def get_riot_game(
    mh_url: str, get_timeline: bool = False, add_names: bool = False, infer_team_names: bool = True
) -> lol_dto.classes.game.LolGame:
    """Returns a LolGame for the given match history URL.

    Params:
        mh_url: a Riot match history URL, containing the game hash.
        get_timeline: whether or not to query the /timeline/ endpoints for the games.
        add_names: whether or not to add champions/items/runes names next to their objects through lol_id_tools.

    Returns:
        A LolGame with all available information.
    """
    parsed_url = urllib.parse.urlparse(urllib.parse.urlparse(mh_url).fragment)
    query = urllib.parse.parse_qs(parsed_url.query)

    platform_id, game_id = parsed_url.path.split("/")[1:3]

    if "gameHash" in query:
        game_hash = query["gameHash"][0]
        match_query = (
            acs.get_game,
            platform_id,
            game_id,
            game_hash,
        )
        timeline_query = (
            acs.get_game_timeline,
            platform_id,
            game_id,
            game_hash,
        )
    else:
        # This is a live game, we just use Riotwatcher
        match_query = (
            lol_watcher.match.by_id,
            platform_id,
            game_id,
        )
        timeline_query = (
            lol_watcher.match.timeline_by_match,
            platform_id,
            game_id,
        )

    with ThreadPoolExecutor() as executor:
        match_dto_future = executor.submit(*match_query)

        if get_timeline:
            match_timeline_dto_future = executor.submit(*timeline_query)

    game = riot_transmute.match_to_game(match_dto_future.result(), add_names=add_names)

    if get_timeline:
        timeline_game = riot_transmute.match_timeline_to_game(
            match_timeline_dto_future.result(), int(game_id), platform_id, add_names=add_names
        )
        game = lol_dto.utilities.merge_games(game, timeline_game)

    # We cannot get team names in custom games
    if "gameHash" in query and infer_team_names:
        game = infer_and_add_team_names(game, mh_url)

    return game


def infer_and_add_team_names(game: LolGame, mh_url) -> LolGame:
    """Try and infer teams trigrams from player’s in game name.
    """
    for team in game["teams"].values():
        for player in team["players"]:
            # We get team name from the first player in the team’s list
            if "name" not in team:
                team["name"] = player["inGameName"].split(" ")[0]

            # We assert every player has the same tag or raise an info-level log
            try:
                assert player["inGameName"].split(" ")[0] == team["name"]
            except AssertionError:
                logging.info(
                    f"Game with URL {mh_url} has an issue with team tags\n"
                    f'Conflict between team tag {team["name"]} and player {player["inGameName"]}'
                )

    return game

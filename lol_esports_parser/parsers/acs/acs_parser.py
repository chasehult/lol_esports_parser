import logging
import urllib.parse
from concurrent.futures.thread import ThreadPoolExecutor

import lol_dto
import riot_transmute

from lol_esports_parser.dto.series_dto import LolSeries, create_series
from lol_esports_parser.parsers.acs.acs_access import ACS

acs = ACS()


def get_acs_series(mh_url_list: list, get_timeline: bool = False, add_names: bool = False) -> LolSeries:
    games_futures = []
    with ThreadPoolExecutor() as executor:
        for mh_url in mh_url_list:
            games_futures.append(executor.submit(get_acs_game, mh_url, get_timeline, add_names))

    return create_series([g.result() for g in games_futures])


def get_acs_game(mh_url: str, get_timeline: bool = False, add_names: bool = False) -> lol_dto.classes.game.LolGame:
    """Returns a LolGame for the given match history URL.

    Params:
        mh_url: a Riot match history URL, containing the game hash.
        get_timeline: whether to retrieve the timeline object and merge it in a single LolGame.
        add_names: whether to add objects names for human readability.
    """
    parsed_url = urllib.parse.urlparse(urllib.parse.urlparse(mh_url).fragment)
    query = urllib.parse.parse_qs(parsed_url.query)

    platform_id, game_id = parsed_url.path.split("/")[1:]
    game_hash = query["gameHash"][0]

    with ThreadPoolExecutor() as executor:
        match_dto_future = executor.submit(acs.get_game, platform_id, game_id, game_hash)

        if get_timeline:
            match_timeline_dto_future = executor.submit(acs.get_game_timeline, platform_id, game_id, game_hash)

    game = riot_transmute.match_to_game(match_dto_future.result(), add_names=add_names)

    if get_timeline:
        timeline_game = riot_transmute.match_timeline_to_game(
            match_timeline_dto_future.result(), int(game_id), platform_id, add_names=add_names
        )
        game = lol_dto.utilities.merge_games(game, timeline_game)

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
                    f"Game {mh_url} has an issue with team tags\n"
                    f'Conflict between team tag {team["name"]} and player {player["inGameName"]}'
                )

    return game

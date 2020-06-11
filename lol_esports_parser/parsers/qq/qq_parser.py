import datetime
import json
import logging
from concurrent.futures.thread import ThreadPoolExecutor

import dateparser

import lol_id_tools as lit
import lol_dto

from lol_esports_parser.dto.series_dto import LolSeries, create_series
from lol_esports_parser.parsers.qq.qq_access import get_qq_games_list, get_all_qq_game_info
from lol_esports_parser.parsers.qq.rune_tree_handler import RuneTreeHandler


rune_tree_handler = RuneTreeHandler()


def get_qq_series_dto(qq_match_url: str, patch: str = None) -> LolSeries:
    """Returns a LolSeriesDto.

    Params:
        qq_url: the qq url of the full match, usually acquired from Leaguepedia.
        patch: if given will use patch information to infer rune tree information.

    Returns:
        A LolSeries.
    """

    game_id_list = get_qq_games_list(qq_match_url)

    games_futures = []
    with ThreadPoolExecutor() as executor:
        for qq_game_object in game_id_list:
            games_futures.append(executor.submit(parse_qq_game, int(qq_game_object["sMatchId"]), patch))

    return create_series([g.result() for g in games_futures])


def parse_qq_game(qq_game_id: int, patch: str = None) -> lol_dto.classes.game.LolGame:
    """Parses a QQ game and returns a LolGameDto.

    Params:
        qq_id: the qq game id, acquired from qq’s match list endpoint and therefore a string.
        patch: optional patch to include in the object

    Returns:
        A LolGameDto.
    """
    game_info, team_info, runes_info, qq_server_id, qq_battle_id = get_all_qq_game_info(qq_game_id)

    # blue_team_id = game_info['sMatchInfo']['BlueTeam']
    # red_team_id = game_info['sMatchInfo']['TeamA'] \
    #     if blue_team_id == game_info['sMatchInfo']['TeamB'] \
    #     else game_info['sMatchInfo']['TeamB']
    # winner = 'BLUE' if blue_team_id == game_info['sMatchInfo']['MatchWin'] else 'RED'

    blue_team_id = team_info["blue_clan_id_"]
    blue_team_name = team_info["blue_clan_name_"]

    red_team_id = team_info["red_clan_id_"]
    red_team_name = team_info["red_clan_name_"]

    winner = "BLUE" if blue_team_id == team_info["win_clan_id_"] else "RED"

    # We start by building the root of the game object

    # The "id" field is the url you use for the first endpoint and should be enough
    qq_source = {"qq": {"id": int(qq_game_id), "server": qq_server_id, "battleId": qq_battle_id}}

    lol_game_dto = lol_dto.classes.game.LolGame(
        sources=qq_source,
        gameInSeries=int(game_info["sMatchInfo"]["MatchNum"]),
        teams={
            "BLUE": lol_dto.classes.game.LolGameTeam(
                name=blue_team_name, uniqueIdentifiers={"qq": {"id": blue_team_id}}
            ),
            "RED": lol_dto.classes.game.LolGameTeam(name=red_team_name, uniqueIdentifiers={"qq": {"id": red_team_id}}),
        },
        winner=winner,
    )

    if patch:
        lol_game_dto["patch"] = patch

    # This is a json inside the json of game_info
    battle_data = json.loads(game_info["battleInfo"]["BattleData"])

    # The 'game-time' field sometimes has sub-second digits that we cut
    date_time = dateparser.parse(f"{battle_data['game-date']}T{battle_data['game-time'][:8]}")
    date_time = date_time.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
    iso_date = date_time.isoformat(timespec="seconds")

    lol_game_dto["start"] = iso_date
    lol_game_dto["duration"] = int(battle_data["game-period"])

    for team_side in ["left", "right"]:
        is_team_a = team_side == "right"
        # Is Team A and Team A is blue -> blue, Is not team A and team A is not blue -> blue
        if is_team_a == (game_info["sMatchInfo"]["TeamA"] == blue_team_id):
            team_color = "BLUE"
        else:
            team_color = "RED"

        # Sometimes the firstTower field isn’t there and needs to be calculated from the players
        if "firstTower" in battle_data[team_side]:
            first_tower = bool(battle_data[team_side]["firstTower"])
        else:
            first_tower = True in (bool(player["firstTower"]) for player in battle_data[team_side]["players"])

        lol_game_dto["teams"][team_color].update(
            {
                "baronKills": int(battle_data[team_side]["b-dragon"]),
                "dragonKills": int(battle_data[team_side]["s-dragon"]),
                "firstTower": first_tower,
                "towerKills": int(battle_data[team_side]["tower"]),
                "players": [],
                "bans": [
                    int(battle_data[team_side][f"ban-hero-{ban_number}"])
                    for ban_number in range(1, 6)
                    if f"ban-hero-{ban_number}" in battle_data[team_side]
                ],
            }
        )

        lol_game_dto["teams"][team_color]["bansNames"] = [
            lit.get_name(i) for i in lol_game_dto["teams"][team_color]["bans"]
        ]

        # Sometimes, not all 5 bans are there for some reason
        if lol_game_dto["teams"][team_color]["bans"].__len__() < 5:
            logging.info(f"Full bans information missing for QQ game with id {qq_game_id}")

        # Then, we iterate on individual player information
        for player_battle_data in battle_data[team_side]["players"]:
            player = parse_player_battle_data(player_battle_data)

            # We need to grab some information back in game_info
            match_member = next(p for p in game_info["sMatchMember"] if p["GameName"] == player["inGameName"])

            player["uniqueIdentifiers"] = {
                "qq": {"accountId": match_member["AccountId"], "memberId": match_member["MemberId"]}
            }

            player_runes = next(p for p in runes_info if p["hero_id_"] == player["championId"])

            player["runes"] = []
            for rune_index, rune in enumerate(player_runes["runes_info_"]["runes_list_"]):
                # slot is 0 for keystones, 1 for first rune of primary tree, ...
                # rank is 1 for most keystones, except stat perks that can be 2
                player["runes"].append(
                    lol_dto.classes.game.LolGamePlayerRune(
                        id=rune["runes_id_"],
                        name=lit.get_name(rune["runes_id_"], object_type="rune"),
                        slot=rune_index,
                        rank=rune["runes_num_"],
                    )
                )

            # We need patch information to properly load rune tree names
            if patch:
                player["primaryRuneTreeId"], player["primaryRuneTreeName"] = rune_tree_handler.get_primary_tree(
                    player["runes"], patch
                )
                player["secondaryRuneTreeId"], player["secondaryRuneTreeName"] = rune_tree_handler.get_secondary_tree(
                    player["runes"], patch
                )

            lol_game_dto["teams"][team_color]["players"].append(player)

    return lol_game_dto


def parse_player_battle_data(player_battle_data: dict) -> lol_dto.classes.game.LolGamePlayer:
    end_of_game_stats = lol_dto.classes.game.LolGamePlayerStats(
        kills=int(player_battle_data["kill"]),
        deaths=int(player_battle_data["death"]),
        assists=int(player_battle_data["assist"]),
        gold=int(player_battle_data["gold"]),
        cs=int(player_battle_data["lasthit"]),
        level=int(player_battle_data["level"]),
        # We cast boolean statistics as proper booleans
        firstBlood=bool(player_battle_data["firstBlood"]),
        firstTower=bool(player_battle_data["firstTower"]),
        # Then we add other numerical statistics
        killingSprees=int(player_battle_data["killingSprees"]),
        doubleKills=int(player_battle_data["dKills"]),
        tripleKills=int(player_battle_data["tKills"]),
        quadraKills=int(player_battle_data["qKills"]),
        pentaKills=int(player_battle_data["pKills"]),
        towerKills=int(player_battle_data["towerKills"]),
        monsterKills=int(player_battle_data["neutralKilled"]),
        monsterKillsInAlliedJungle=int(player_battle_data["neutralKilledTJungle"]),
        monsterKillsInEnemyJungle=int(player_battle_data["neutralKilledEJungle"]),
        wardsPlaced=int(player_battle_data["wardsPlaced"]),
        wardsKilled=int(player_battle_data["wardsKilled"]),
        visionWardsBought=int(player_battle_data["visionWardsBought"]),
        # Damage totals, using a nomenclature close to match-v4
        totalDamageDealt=int(player_battle_data["totalDamage"]),
        totalDamageDealtToChampions=int(player_battle_data["totalDamageToChamp"]),
        physicalDamageDealtToChampions=int(player_battle_data["pDamageToChamp"]),
        magicDamageDealtToChampions=int(player_battle_data["mDamageDealtToChamp"]),
        totalDamageTaken=int(player_battle_data["totalDamageTaken"]),
        physicalDamageTaken=int(player_battle_data["pDamageTaken"]),
        magicDamageTaken=int(player_battle_data["mDamageTaken"]),
        items=[
            lol_dto.classes.game.LolGamePlayerItem(
                id=int(player_battle_data["equip"][key]),
                name=lit.get_name(player_battle_data["equip"][key], object_type="item"),
                slot=int(key[-1]),
            )
            for key in player_battle_data["equip"]
        ],
    )

    # TODO Check how to raise the error only once
    for field_name in ["largestCriticalStrike", "largestKillingSpree", "inhibitorKills", "totalHeal"]:
        if field_name in player_battle_data:
            end_of_game_stats[field_name] = int(player_battle_data[field_name])

    if "pDamageDealt" in player_battle_data:
        end_of_game_stats["physicalDamageDealt"] = int(player_battle_data["pDamageDealt"])
    if "mDamageDealt" in player_battle_data:
        end_of_game_stats["magicDamageDealt"] = int(player_battle_data["mDamageDealt"])

    return lol_dto.classes.game.LolGamePlayer(
        # This is the raw player name in the game
        inGameName=player_battle_data["name"],
        championId=int(player_battle_data["hero"]),
        championName=lit.get_name(player_battle_data["hero"], object_type="champion"),
        # Summoner spells are a list ordered as D -> F summoner spell
        summonerSpells=[
            lol_dto.classes.game.LolGamePlayerSummonerSpell(
                id=int(player_battle_data[skill_key]),
                name=lit.get_name(player_battle_data[skill_key], object_type="summoner_spell"),
                slot=int(skill_key[-1]),
            )
            for skill_key in ["skill-1", "skill-2"]
        ],
        endOfGameStats=end_of_game_stats,
    )

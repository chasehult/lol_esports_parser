import json
from datetime import timezone
import dateparser
from collections import Counter

import lol_id_tools as lit
import lol_dto

from lol_esports_parser.dto.series_dto import LolSeries
from lol_esports_parser.parsers.qq.qq_access import get_qq_games_list, get_all_qq_game_info


def get_qq_series_dto(qq_match_url: str) -> LolSeries:
    """Returns a LolSeriesDto.

    Params:
        qq_url: the qq url of the full match, usually acquired from Leaguepedia.

    Returns:
        A LolSeries.
    """

    game_id_list = get_qq_games_list(qq_match_url)

    games = []  # List of LolGame DTOs representing the match
    for game in game_id_list:
        games.append(parse_qq_game(int(game["sMatchId"])))

    # Making extra sure they’re in the right order
    games = sorted(games, key=lambda x: x["start"])

    # We get the team names from the first game
    team_names = [games[0]["teams"][team_side]["name"] for team_side in ["BLUE", "RED"]]
    team_scores = Counter({team_name: 0 for team_name in team_names})

    for lol_game_dto in games:
        for team_side, team in lol_game_dto["teams"].items():
            if lol_game_dto["winner"] == team_side:
                team_scores[team["name"]] += 1

    return LolSeries(score=dict(team_scores), winner=team_scores.most_common(1)[0][0], games=games)


def parse_qq_game(qq_game_id: int) -> lol_dto.classes.game.LolGame:
    """Parses a QQ game and returns a LolGameDto.

    Params:
        qq_id: the qq game id, acquired from qq’s match list endpoint and therefore a string.

    Returns:
        A LolGameDto.
    """
    game_info, team_info, runes_info, qq_server_id, qq_battle_id = get_all_qq_game_info(qq_game_id)

    # TODO This code is here for when the second endpoint does not work
    # blue_team_id = game_info['sMatchInfo']['BlueTeam']
    # red_team_id = game_info['sMatchInfo']['TeamA'] \
    #     if blue_team_id == game_info['sMatchInfo']['TeamB'] \
    #     else game_info['sMatchInfo']['TeamB']
    # winner = 'blue' if blue_team_id == game_info['sMatchInfo']['MatchWin'] else 'red'

    blue_team_id = team_info["blue_clan_id_"]
    blue_team_name = team_info["blue_clan_name_"]

    red_team_id = team_info["red_clan_id_"]
    red_team_name = team_info["red_clan_name_"]

    winner = "BLUE" if blue_team_id == team_info["win_clan_id_"] else "RED"

    # We start by building the root of the game object
    qq_source = {"qq": {"id": int(qq_game_id), "server": qq_server_id, "battleId": qq_battle_id}}

    # TODO Should game_info["sMatchInfo"]["GameName"] be added somewhere?

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

    # This is a json inside the json of game_info
    battle_data = json.loads(game_info["battleInfo"]["BattleData"])

    date_time = dateparser.parse(f"{battle_data['game-date']} {battle_data['game-time']}")
    date_time = date_time.replace(tzinfo=timezone.utc)
    iso_date = date_time.isoformat(timespec="seconds")

    lol_game_dto["start"] = iso_date
    lol_game_dto["duration"] = int(battle_data["game-period"])

    # TODO Parse bans
    for team in ["left", "right"]:
        is_team_a = team == "right"
        # Is Team A and Team A is blue -> blue, Is not team A and team A is not blue -> blue
        if is_team_a == (game_info["sMatchInfo"]["TeamA"] == blue_team_id):
            team_side = "BLUE"
        else:
            team_side = "RED"

        # TODO Add kills and gold totals
        lol_game_dto["teams"][team_side].update(
            {
                "baronKills": int(battle_data[team]["b-dragon"]),
                "dragonKills": int(battle_data[team]["s-dragon"]),
                "firstTower": bool(battle_data[team]["firstTower"]),
                "towerKills": int(battle_data[team]["tower"]),
                "players": [],
            }
        )

        for role_index, player_battle_data in enumerate(battle_data[team]["players"]):
            player = parse_player_battle_data(player_battle_data)

            # We go grab some information back in game_info
            match_member = next(p for p in game_info["sMatchMember"] if p["GameName"] == player["inGameName"])

            player["uniqueIdentifiers"] = {
                "qq": {"accountId": match_member["AccountId"], "memberId": match_member["MemberId"]}
            }

            # TODO See if we can match it another way than champion ID
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

            # TODO Add PrimaryTree/SecondaryTree info

            lol_game_dto["teams"][team_side]["players"].append(player)

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
        largestKillingSpree=int(player_battle_data["largestKillingSpree"]),
        doubleKills=int(player_battle_data["dKills"]),
        tripleKills=int(player_battle_data["tKills"]),
        quadraKills=int(player_battle_data["qKills"]),
        pentaKills=int(player_battle_data["pKills"]),
        towerKills=int(player_battle_data["towerKills"]),
        inhibitorKills=int(player_battle_data["inhibitorKills"]),
        monsterKills=int(player_battle_data["neutralKilled"]),
        monsterKillsInAlliedJungle=int(player_battle_data["neutralKilledTJungle"]),
        monsterKillsInEnemyJungle=int(player_battle_data["neutralKilledEJungle"]),
        wardsPlaced=int(player_battle_data["wardsPlaced"]),
        wardsKilled=int(player_battle_data["wardsKilled"]),
        visionWardsBought=int(player_battle_data["visionWardsBought"]),
        largestCriticalStrike=int(player_battle_data["largestCriticalStrike"]),
        # Damage totals, using a nomenclature close to match-v4
        totalDamageDealt=int(player_battle_data["totalDamage"]),
        physicalDamageDealt=int(player_battle_data["pDamageDealt"]),
        magicDamageDealt=int(player_battle_data["mDamageDealt"]),
        totalDamageDealtToChampions=int(player_battle_data["totalDamageToChamp"]),
        physicalDamageDealtToChampions=int(player_battle_data["pDamageToChamp"]),
        magicDamageDealtToChampions=int(player_battle_data["mDamageDealtToChamp"]),
        totalDamageTaken=int(player_battle_data["totalDamageTaken"]),
        physicalDamageTaken=int(player_battle_data["pDamageTaken"]),
        magicDamageTaken=int(player_battle_data["mDamageTaken"]),
        totalHeal=int(player_battle_data["totalHeal"]),
        items=[
            lol_dto.classes.game.LolGamePlayerItem(
                id=int(player_battle_data["equip"][key]),
                name=lit.get_name(player_battle_data["equip"][key], object_type="item"),
                slot=int(key[-1]),
            )
            for key in player_battle_data["equip"]
        ],
    )

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

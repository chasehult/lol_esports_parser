import datetime
import json
import logging
from concurrent.futures.thread import ThreadPoolExecutor
from json import JSONDecodeError
from typing import List

import dateparser

import lol_id_tools as lit
import lol_dto

from lol_esports_parser.dto.qq_source import SourceQQ
from lol_esports_parser.dto.series_dto import LolSeries, create_series
from lol_esports_parser.parsers.qq.qq_access import get_qq_games_list, get_all_qq_game_info
from lol_esports_parser.parsers.rune_tree_handler import RuneTreeHandler


rune_tree_handler = RuneTreeHandler()
roles = {"1": "TOP", "5": "JGL", "2": "MID", "3": "BOT", "4": "SUP"}


def get_qq_series(qq_match_url: str, patch: str = None, add_names: bool = True) -> LolSeries:
    """Returns a LolSeriesDto.

    Params:
        qq_url: the qq url of the full match, usually acquired from Leaguepedia.
        get_timeline: whether or not to query the /timeline/ endpoints for the games.
        add_names: whether or not to add champions/items/runes names next to their objects through lol_id_tools.

    Returns:
        A LolSeries.
    """

    game_id_list = get_qq_games_list(qq_match_url)

    games_futures = []
    with ThreadPoolExecutor() as executor:
        for qq_game_object in game_id_list:
            games_futures.append(executor.submit(parse_qq_game, int(qq_game_object["sMatchId"]), patch, add_names))

    return create_series([g.result() for g in games_futures])


def parse_qq_game(qq_game_id: int, patch: str = None, add_names: bool = True) -> lol_dto.classes.game.LolGame:
    """Parses a QQ game and returns a LolGameDto.

    Params:
        qq_game_̤d: the qq game id, acquired from qq’s match list endpoint.
        patch: optional patch to include in the object and query rune trees.
        add_names: whether or not to add champions/items/runes names next to their objects through lol_id_tools.

    Returns:
        A LolGameDto.
    """

    game_info, team_info, runes_info, qq_server_id, qq_battle_id = get_all_qq_game_info(qq_game_id)

    log_prefix = (
        f"match {game_info['sMatchInfo']['bMatchId']}|"
        f"game {game_info['sMatchInfo']['MatchNum']}|"
        f"id {qq_game_id}:\t"
    )
    logging.debug(f"{log_prefix}Starting parsing")

    # We start by building the root of the game object
    lol_game_dto = lol_dto.classes.game.LolGame(
        sources={"qq": SourceQQ(id=int(qq_game_id), serverId=qq_server_id, battleId=qq_battle_id)},
        gameInSeries=int(game_info["sMatchInfo"]["MatchNum"]),
        teams={},
    )

    warnings = set()
    info = set()

    try:
        # The 'BattleTime' field sometimes has sub-second digits that we cut
        date_time = dateparser.parse(
            f"{game_info['battleInfo']['BattleDate']}T{game_info['battleInfo']['BattleTime'][:8]}"
        )
        date_time = date_time.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
        lol_game_dto["start"] = date_time.isoformat(timespec="seconds")
    except KeyError:
        info.add(f"{log_prefix}Missing ['game']['start']")

    if patch:
        lol_game_dto["patch"] = patch

    # Get blue and red team IDs through the BlueTeam field in the first JSON
    blue_team_id = int(game_info["sMatchInfo"]["BlueTeam"])
    red_team_id = int(
        game_info["sMatchInfo"]["TeamA"]
        if game_info["sMatchInfo"]["BlueTeam"] == game_info["sMatchInfo"]["TeamB"]
        else game_info["sMatchInfo"]["TeamB"]
    )

    # TODO Write that in a more beautiful way
    # The MatchWin field refers to TeamA/TeamB, which are not blue/red
    if game_info["sMatchInfo"]["MatchWin"] == "1":
        if int(game_info["sMatchInfo"]["TeamA"]) == blue_team_id:
            lol_game_dto["winner"] = "BLUE"
        else:
            lol_game_dto["winner"] = "RED"
    elif game_info["sMatchInfo"]["MatchWin"] == "2":
        if int(game_info["sMatchInfo"]["TeamB"]) == blue_team_id:
            lol_game_dto["winner"] = "BLUE"
        else:
            lol_game_dto["winner"] = "RED"

    # Handle battle_data parsing and game-related information
    try:
        # This is a json inside the json of game_info
        battle_data = json.loads(game_info["battleInfo"]["BattleData"])
        lol_game_dto["duration"] = int(battle_data["game-period"])

    except JSONDecodeError:
        # Usually means the field was empty
        battle_data = {}

    # Match name usually look like TES vs EDG but some casing typos can be caught here
    possible_team_names = game_info["sMatchInfo"]["bMatchName"].lower().split("vs")  # Used if team_info is not there
    possible_team_names = [n.replace(" ", "").upper() for n in possible_team_names]

    # We iterate of the two team IDs from sMatchInfo
    for team_id in blue_team_id, red_team_id:
        team_color = "BLUE" if team_id == blue_team_id else "RED"

        team = lol_dto.classes.game.LolGameTeam(uniqueIdentifiers={"qq": {"id": team_id}}, players=[])

        # We start by getting as much information as possible from the sMatchMember fields
        for match_member in game_info["sMatchMember"]:
            # We match players on the team id
            if int(match_member["TeamId"]) != team_id:
                continue

            player = lol_dto.classes.game.LolGamePlayer(
                inGameName=match_member["GameName"],
                role=roles[match_member["Place"]],
                championId=int(match_member["ChampionId"]),
                endOfGameStats=lol_dto.classes.game.LolGamePlayerEndOfGameStats(
                    kills=int(match_member["Game_K"]),
                    deaths=int(match_member["Game_D"]),
                    assists=int(match_member["Game_A"]),
                    gold=int(match_member["Game_M"]),
                ),
                uniqueIdentifiers={
                    "qq": {"accountId": int(match_member["AccountId"]), "memberId": int(match_member["MemberId"])}
                },
            )

            if add_names:
                player["championName"] = lit.get_name(player["championId"], object_type="champion")

            team["players"].append(player)

            # We get the tentative team name
            # We cast team names and player names as lowercase because they made the mistake in some old games
            tentative_team_name = next(t for t in possible_team_names if t.lower() in match_member["GameName"].lower())

        # If we have info from the second endpoint we use it to validate team id and game winner
        if team_info:
            try:
                assert team_id == team_info[f"{team_color.lower()}_clan_id_"]

                team["name"] = team_info[f"{team_color.lower()}_clan_name_"]

                if team_id == team_info["win_clan_id_"]:
                    assert lol_game_dto["winner"] == team_color

            except AssertionError:
                warnings.add(f"{log_prefix}⚠ Inconsistent team sides between endpoints ⚠")
                info.add(f"{log_prefix}Team sides might be wrong")

                # We use the tentative team name from the first object instead
                team["name"] = tentative_team_name

                try:
                    # In the games with this issue, the second endpoint was the one with the right side information
                    team_color = next(
                        color for color in ("blue", "red") if team_info[f"{color}_clan_id_"] == team_id
                    ).upper()
                except StopIteration:
                    # When we cannot find a team with the same ID as the one in the first object, we drop the process
                    continue

                if team_info["win_clan_id_"] == team_id:
                    lol_game_dto["winner"] = team_color

        # If it is missing, we log what we are missing and try to guess team names from players
        else:
            info.add(f"{log_prefix}Missing ['team']['name'], guessing them from game name")
            info.add(f"{log_prefix}Missing ['player']['runes']")

            team["name"] = tentative_team_name

        # Without "battle data", we stop there
        # We also check both teams have the "players" field as we found games without it, and battleData was faulty
        if not battle_data or any(len(battle_data[team_side]["players"]) != 5 for team_side in ("left", "right")):
            warnings.add(f"{log_prefix}⚠ Missing 'BattleData', meaning almost all end of game stats ⚠")
            lol_game_dto["teams"][team_color] = team
            continue

        # Finding left/right team side through player names
        # TODO Make that a bit more palatable
        for tentative_team_side in "left", "right":
            # We just look at the first player
            player = battle_data[tentative_team_side]["players"][0]

            for match_member in game_info["sMatchMember"]:
                if player["name"] == match_member["GameName"] and int(match_member["TeamId"]) == team_id:
                    team_side = tentative_team_side

        # Sometimes the firstTower field isn’t in battleData but it can be calculated from the players
        if "firstTower" in battle_data[team_side]:
            first_tower = bool(battle_data[team_side]["firstTower"])
        else:
            first_tower = True in (bool(player["firstTower"]) for player in battle_data[team_side]["players"])

        # We fill more team related information
        team["bans"] = [
            int(battle_data[team_side][f"ban-hero-{ban_number}"])
            for ban_number in range(1, 6)
            if f"ban-hero-{ban_number}" in battle_data[team_side]
        ]

        team["endOfGameStats"] = lol_dto.classes.game.LolGameTeamEndOfGameStats(
            towerKills=int(battle_data[team_side]["tower"]),
            baronKills=int(battle_data[team_side]["b-dragon"]),
            dragonKills=int(battle_data[team_side]["s-dragon"]),
            firstTower=first_tower,
        )

        # We add ban names from the bans field
        if add_names:
            team["bansNames"] = [lit.get_name(i, object_type="champion") for i in team["bans"]]

        # Bans are sometimes incomplete
        if team["bans"].__len__() < 5:
            info.add(f"{log_prefix}Missing ['team']['bans']")

        # Finally, we look at per-player BattleData
        for player_battle_data in battle_data[team_side]["players"]:
            player = next(p for p in team["players"] if player_battle_data["name"] == p["inGameName"])

            # Updating missing fields for logging
            try:
                info.update(
                    [
                        f"{log_prefix}Missing ['player'][{field}]"
                        for field in parse_player_battle_data(player, player_battle_data, add_names)
                    ]
                )
            except ValueError:
                warnings.add(f"{log_prefix}⚠ Missing most end of game stats ⚠")
                warnings.add(f"{log_prefix}⚠ Missing runes ⚠")
                warnings.add(f"{log_prefix}⚠ Bans are likely wrong ⚠")
                continue

            try:
                add_runes(player, runes_info, patch, add_names)
            except StopIteration:
                info.add(f"{log_prefix}Missing ['player']['runes']")

        # Finally, we insert the team
        lol_game_dto["teams"][team_color] = team

    for warning in warnings:
        logging.warning(warning)

    for log in info:
        logging.info(log)

    return lol_game_dto


def add_runes(player: lol_dto.classes.game.LolGamePlayer, runes_info, patch, add_names=True):
    player_runes = next(p for p in runes_info if p["hero_id_"] == player["championId"])

    player["runes"] = []
    for rune_index, rune in enumerate(player_runes["runes_info_"]["runes_list_"]):
        # slot is 0 for keystones, 1 for first rune of primary tree, ...
        # rank is 1 for most keystones, except stat perks that can be 2
        rune = lol_dto.classes.game.LolGamePlayerRune(id=rune["runes_id_"], slot=rune_index, rank=rune["runes_num_"],)

        if add_names:
            rune["name"] = lit.get_name(rune["id"], object_type="rune")

        player["runes"].append(rune)

    # We need patch information to properly load rune tree names
    if patch:
        player["primaryRuneTreeId"], player["primaryRuneTreeName"] = rune_tree_handler.get_primary_tree(
            player["runes"], patch
        )
        (player["secondaryRuneTreeId"], player["secondaryRuneTreeName"],) = rune_tree_handler.get_secondary_tree(
            player["runes"], patch
        )

    return player


def parse_player_battle_data(
    player: lol_dto.classes.game.LolGamePlayer, player_battle_data: dict, add_names: bool
) -> List[str]:

    missing_fields = []

    try:
        # We start by verifying champion ID is coherent
        assert player["championId"] == int(player_battle_data["hero"])
    except AssertionError:
        # In the games with buggy championId, almost all fields were empty, we raise
        raise ValueError

    end_of_game_stats = lol_dto.classes.game.LolGamePlayerEndOfGameStats(
        kills=int(player_battle_data["kill"]),
        deaths=int(player_battle_data["death"]),
        assists=int(player_battle_data["assist"]),
        gold=int(player_battle_data["gold"]),
        cs=int(player_battle_data["lasthit"]),
        level=int(player_battle_data["level"]),
        items=[],
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
    )

    for item_key in player_battle_data["equip"]:
        item = lol_dto.classes.game.LolGamePlayerItem(
            id=int(player_battle_data["equip"][item_key]), slot=int(item_key[-1]),
        )

        if add_names:
            item["name"] = lit.get_name(item["id"], object_type="item")

        end_of_game_stats["items"].append(item)

    # We validate the fields from sMatchMember
    assert end_of_game_stats["kills"] == player["endOfGameStats"]["kills"]
    assert end_of_game_stats["deaths"] == player["endOfGameStats"]["deaths"]
    assert end_of_game_stats["assists"] == player["endOfGameStats"]["assists"]
    assert end_of_game_stats["gold"] == player["endOfGameStats"]["gold"]

    # We check fields that are regularly missing

    for field_name in ["largestCriticalStrike", "largestKillingSpree", "inhibitorKills", "totalHeal"]:
        if field_name in player_battle_data:
            end_of_game_stats[field_name] = int(player_battle_data[field_name])
        else:
            missing_fields.append(field_name)

    if "pDamageDealt" in player_battle_data:
        end_of_game_stats["physicalDamageDealt"] = int(player_battle_data["pDamageDealt"])
    else:
        missing_fields.append("pDamageDealt")

    if "mDamageDealt" in player_battle_data:
        end_of_game_stats["magicDamageDealt"] = int(player_battle_data["mDamageDealt"])
    else:
        missing_fields.append("mDamageDealt")

    # Finally, we write them to the player object
    player["endOfGameStats"] = end_of_game_stats

    player["summonerSpells"] = []

    for skill_key in "skill-1", "skill-2":
        summoner_spell = lol_dto.classes.game.LolGamePlayerSummonerSpell(
            id=int(player_battle_data[skill_key]), slot=int(skill_key[-1]),
        )

        if add_names:
            summoner_spell["name"] = lit.get_name(summoner_spell["id"], object_type="summoner_spell")

        player["summonerSpells"].append(summoner_spell)

    return missing_fields

import json
import logging
import urllib.parse
import requests

from lol_esports_parser.config import endpoints


def get_qq_games_list(qq_match_url):
    """Gets a games list from a QQ series match history URL.

    Relies on having bmid=xxx in the URL.
    """
    parsed_url = urllib.parse.urlparse(qq_match_url)
    qq_match_id = urllib.parse.parse_qs(parsed_url.query)["bmid"][0]

    games_list_query_url = f"{endpoints['qq']['match_list']}{qq_match_id}"

    logging.debug(f"Querying {games_list_query_url}")
    response = requests.get(games_list_query_url)

    return response.json()["msg"]


def get_all_qq_game_info(qq_game_id: int):
    game_info = get_basic_qq_game_info(qq_game_id)

    qq_server_id = int(game_info["sMatchInfo"]["AreaId"])
    qq_battle_id = int(game_info["sMatchInfo"]["BattleId"])

    # TODO Handle this endpoint not working
    team_info = get_team_info(qq_server_id, qq_battle_id)
    qq_world_id = team_info["world_"]
    qq_room_id = team_info["room_id_"]

    runes_info = get_runes_info(qq_world_id, qq_room_id)

    return game_info, team_info, runes_info, qq_server_id, qq_battle_id


def get_basic_qq_game_info(qq_game_id: int):
    """Gets the basic info about the game, including sides and end of game stats for players.
    """

    game_query_url = f"{endpoints['qq']['match_info']}{qq_game_id}"

    logging.debug(f"Querying {game_query_url}")
    response = requests.get(game_query_url)

    return response.json()["msg"]


def get_team_info(qq_server_id, qq_battle_id):
    """Gets team-specific information, but also world_id and room_id for runes queries.
    """
    team_info_url = (
        endpoints["qq"]["battle_info"].replace("BATTLE_ID", str(qq_battle_id)).replace("WORLD_ID", str(qq_server_id))
    )

    logging.debug(f"Querying {team_info_url}")
    response = requests.get(team_info_url)

    return json.loads(response.json()["msg"])["battle_list_"][0]


def get_runes_info(qq_world_id, qq_room_id):
    """Gets runes lists per players.
    """
    runes_info_url = endpoints["qq"]["runes"].replace("WORLD_ID", str(qq_world_id)).replace("ROOM_ID", str(qq_room_id))

    logging.debug(f"Querying {runes_info_url}")
    response = requests.get(runes_info_url)

    return json.loads(response.json()["msg"])["hero_list_"]

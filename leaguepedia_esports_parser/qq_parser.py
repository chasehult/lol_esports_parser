import json
import logging
import dateparser
import urllib.parse as urlparse
from typing import List
import requests
from leaguepedia_esports_parser.config import endpoints
from leaguepedia_esports_parser.qq_team_name_handler import get_team_name


def get_all_games_dto(qq_match_url: str) -> List[dict]:
    """Returns a LolGameDto for each game in the match.

    Params:
        qq_url: the qq url of the full match, usually acquired from Leaguepedia

    Returns:
        A list of LolGameDto for each game in the match.
    """
    parsed_url = urlparse.urlparse(qq_match_url)
    match_qq_id = urlparse.parse_qs(parsed_url.query)['bmid'][0]

    games_list_query_url = f"{endpoints['qq']['match_list']}{match_qq_id}"

    logging.info(f'Querying {games_list_query_url}')
    response = requests.get(games_list_query_url)

    games_list = response.json()['msg']

    dto_list = []
    for game in games_list:
        dto_list.append(parse_qq_game(game['sMatchId']))

    return dto_list


def parse_qq_game(qq_game_id: int) -> dict:
    """Parses a QQ game and returns a LolGameDto.

    Params:
        qq_id: the qq game id, acquired from qq’s match list endpoint

    Returns:
        A LolGameDto.
    """
    game_info = get_game_info(qq_game_id)

    blue_team = game_info['sMatchInfo']['BlueTeam']
    red_team = game_info['sMatchInfo']['TeamA'] \
        if blue_team == game_info['sMatchInfo']['TeamB'] \
        else game_info['sMatchInfo']['TeamB']

    lol_game_dto = {'qq_id': qq_game_id,
                    'qq_server': game_info['sMatchInfo']['AreaId'],
                    'qq_battle_id': game_info['sMatchInfo']['BattleId'],
                    'qq_tournament': game_info['sMatchInfo']['GameName'],
                    'game_in_match': game_info['sMatchInfo']['MatchNum'],
                    'teams': {'blue': {'id': blue_team,
                                       'name': get_team_name(blue_team, game_info)},
                              'red': {'id': red_team,
                                      'name': get_team_name(red_team, game_info)}},
                    'winner': 'blue' if blue_team == game_info['sMatchInfo']['MatchWin'] else 'red'
                    }

    battle_data = json.loads(game_info['battleInfo']['BattleData'])

    lol_game_dto['startDate'] = dateparser.parse(f"{battle_data['game-date']} {battle_data['game-time']}")
    lol_game_dto['startTimestamp'] = int(lol_game_dto['startDate'].timestamp() * 1000)

    # TODO check fields names
    # TODO Parse players at the same time
    for team in ['left', 'right']:
        team_side = 'blue' if game_info['sMatchInfo']['TeamA'] == blue_team and team == 'left' else 'red'

        lol_game_dto['teams'][team] = {
            team_side:
                {'b-dragon': battle_data[team_dict]['b-dragon'],
                 's-dragon': battle_data[team_dict]['s-dragon'],
                 'firstBlood': battle_data[team_dict]['firstBlood'],
                 'firstTower': battle_data[team_dict]['firstTower'],
                 'towersKilled': battle_data[team_dict]['tower']}
            for team_dict in ['left', 'right']}

    return lol_game_dto


def get_game_info(qq_game_id: int):
    game_query_url = f"{endpoints['qq']['match_info']}{qq_game_id}"

    logging.info(f'Querying {game_query_url}')
    response = requests.get(game_query_url)

    return response.json()['msg']

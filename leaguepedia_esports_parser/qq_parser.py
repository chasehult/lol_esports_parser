import json
import logging
import dateparser
import urllib.parse as urlparse
import requests
from leaguepedia_esports_parser.config import endpoints
from leaguepedia_esports_parser.qq_team_name_handler import get_team_name
import lol_id_tools as lit


def get_qq_series_dto(qq_match_url: str) -> dict:
    """Returns a LolSeriesDto.

    Params:
        qq_url: the qq url of the full match, usually acquired from Leaguepedia

    Returns:
        A LolSeriesDto.
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

    return {'games': dto_list}


def parse_qq_game(qq_game_id: str) -> dict:
    """Parses a QQ game and returns a LolGameDto.

    Params:
        qq_id: the qq game id, acquired from qq’s match list endpoint and therefore a string

    Returns:
        A LolGameDto.
    """
    game_info = get_game_info(qq_game_id)

    blue_team = game_info['sMatchInfo']['BlueTeam']
    red_team = game_info['sMatchInfo']['TeamA'] \
        if blue_team == game_info['sMatchInfo']['TeamB'] \
        else game_info['sMatchInfo']['TeamB']

    lol_game_dto = {'qqID': qq_game_id,
                    'qqServer': game_info['sMatchInfo']['AreaId'],
                    'qqBattleID': game_info['sMatchInfo']['BattleId'],
                    'qqTournament': game_info['sMatchInfo']['GameName'],
                    'gameInMatch': game_info['sMatchInfo']['MatchNum'],
                    'teams': {'blue': {'id': blue_team,
                                       'name': get_team_name(blue_team, game_info)},
                              'red': {'id': red_team,
                                      'name': get_team_name(red_team, game_info)}},
                    'winner': 'blue' if blue_team == game_info['sMatchInfo']['MatchWin'] else 'red',
                    'players': []
                    }

    battle_data = json.loads(game_info['battleInfo']['BattleData'])

    lol_game_dto['startDate'] = dateparser.parse(f"{battle_data['game-date']} {battle_data['game-time']}")
    lol_game_dto['startTimestamp'] = int(lol_game_dto['startDate'].timestamp() * 1000)

    # TODO Check fields names and their meaning
    # TODO Check how to handle bans
    for team in ['left', 'right']:
        team_side = 'blue' if game_info['sMatchInfo']['TeamA'] == blue_team and team == 'left' else 'red'

        lol_game_dto['teams'][team_side].update({'b-dragon': battle_data[team]['b-dragon'],
                                                 's-dragon': battle_data[team]['s-dragon'],
                                                 'firstBlood': battle_data[team]['firstBlood'],
                                                 'firstTower': battle_data[team]['firstTower'],
                                                 'towersKilled': battle_data[team]['tower']})

        for player_battle_data in battle_data[team]['players']:
            lol_game_dto['players'].append(parse_player(player_battle_data, team_side))

    return lol_game_dto


def parse_player(player_battle_data: dict, team_side) -> dict:
    output_dict = {'team': team_side,
                   'kills': player_battle_data['kill'],
                   'deaths': player_battle_data['death'],
                   'assists': player_battle_data['assist'],
                   'gold': player_battle_data['gold'],
                   'timeDead': player_battle_data['deadTime'],
                   'inGameName': player_battle_data['name'],
                   'championId': player_battle_data['hero'],
                   'championName': lit.get_name(player_battle_data['hero'], object_type='champion'),
                   'summonerSpells': [],
                   'items': [],
                   'runes': []}

    for key in player_battle_data['equip']:
        output_dict['items'].append({'itemId': player_battle_data['equip'][key],
                                     'itemName': lit.get_name(player_battle_data['equip'][key], object_type='item'),
                                     'itemSlot': key[-1]})

    return output_dict


def get_game_info(qq_game_id: str):
    game_query_url = f"{endpoints['qq']['match_info']}{qq_game_id}"

    logging.info(f'Querying {game_query_url}')
    response = requests.get(game_query_url)

    return response.json()['msg']

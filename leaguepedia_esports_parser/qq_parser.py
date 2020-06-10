import json
import logging
from collections import Counter

import dateparser
import urllib.parse as urlparse
import requests
from leaguepedia_esports_parser.config import endpoints, roles_list
import lol_id_tools as lit


def get_qq_series_dto(qq_match_url: str) -> dict:
    """Returns a LolSeriesDto.

    Params:
        qq_url: the qq url of the full match, usually acquired from Leaguepedia.

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
        dto_list.append(parse_qq_game(int(game['sMatchId'])))

    # Making extra sure they’re in the right order
    dto_list = sorted(dto_list, key=lambda x: x['startTimestamp'])

    team_names = [dto_list[0]['teams'][team_side]['name'] for team_side in ['blue', 'red']]
    team_scores = Counter({team_name: 0 for team_name in team_names})

    for lol_game_dto in dto_list:
        for team_side, team in lol_game_dto['teams'].items():
            if lol_game_dto['winner'] == team_side:
                team_scores[team['name']] += 1

    return {'games': dto_list,
            'winner': team_scores.most_common(1)[0][0],
            'score': dict(team_scores)}


def parse_qq_game(qq_game_id: int) -> dict:
    """Parses a QQ game and returns a LolGameDto.

    Params:
        qq_id: the qq game id, acquired from qq’s match list endpoint and therefore a string.

    Returns:
        A LolGameDto.
    """
    # First, we make the three queries required to get all the information about the game
    game_info = get_game_info(qq_game_id)

    qq_server_id = int(game_info['sMatchInfo']['AreaId'])
    qq_battle_id = int(game_info['sMatchInfo']['BattleId'])

    # TODO Handle this endpoint not working
    team_info = get_team_info(qq_server_id, qq_battle_id)
    qq_world_id = team_info['world_']
    qq_room_id = team_info['room_id_']

    runes_info = get_runes_info(qq_world_id, qq_room_id)

    # TODO This code is here for when the second endpoint does not work
    # blue_team_id = game_info['sMatchInfo']['BlueTeam']
    # red_team_id = game_info['sMatchInfo']['TeamA'] \
    #     if blue_team_id == game_info['sMatchInfo']['TeamB'] \
    #     else game_info['sMatchInfo']['TeamB']
    # winner = 'blue' if blue_team_id == game_info['sMatchInfo']['MatchWin'] else 'red'

    blue_team_id = team_info['blue_clan_id_']
    blue_team_name = team_info['blue_clan_name_']

    red_team_id = team_info['red_clan_id_']
    red_team_name = team_info['red_clan_name_']

    winner = 'blue' if blue_team_id == team_info['win_clan_id_'] else 'red'

    # We start by building the root of the game object
    lol_game_dto = {'qqId': int(qq_game_id),
                    'qqServer': qq_server_id,
                    'qqBattleId': qq_battle_id,
                    'qqTournament': game_info['sMatchInfo']['GameName'],
                    'gameInSeries': int(game_info['sMatchInfo']['MatchNum']),
                    'teams': {'blue': {'qqId': blue_team_id,
                                       'name': blue_team_name},
                              'red': {'qqId': red_team_id,
                                      'name': red_team_name}
                              },
                    'winner': winner}

    # This is a json inside the json of game_info
    battle_data = json.loads(game_info['battleInfo']['BattleData'])

    # TODO Decide on date format
    # lol_game_dto['startDate'] = dateparser.parse(f"{battle_data['game-date']} {battle_data['game-time']}")

    lol_game_dto['startTimestamp'] = int(
        dateparser.parse(f"{battle_data['game-date']} {battle_data['game-time']}").timestamp() * 1000)

    lol_game_dto['duration'] = int(battle_data['game-period'])

    # TODO Parse bans
    for team in ['left', 'right']:
        # TODO properly understand who’s team A and team B
        is_team_a = team == 'right'
        # Is Team A and Team A is blue -> blue, Is not team A and team A is not blue -> blue
        if is_team_a == (game_info['sMatchInfo']['TeamA'] == blue_team_id):
            team_side = 'blue'
        else:
            team_side = 'red'

        # TODO Add kills and gold totals
        lol_game_dto['teams'][team_side].update({'baronKills': int(battle_data[team]['b-dragon']),
                                                 'dragonKills': int(battle_data[team]['s-dragon']),
                                                 'firstBlood': bool(battle_data[team]['firstBlood']),
                                                 'firstTower': bool(battle_data[team]['firstTower']),
                                                 'towersKilled': int(battle_data[team]['tower']),
                                                 'players': []})

        for role_index, player_battle_data in enumerate(battle_data[team]['players']):
            player = parse_player_battle_data(player_battle_data)

            player['role'] = roles_list[role_index]

            # We go grab some information back in game_info
            match_member = next(p for p in game_info['sMatchMember'] if p['GameName'] == player['inGameName'])

            player['MVP'] = bool(match_member['iMVP'])
            player['qqAccountId'] = bool(match_member['AccountId'])
            player['qqMemberId'] = bool(match_member['MemberId'])

            # TODO See if we can match it another way than champion ID
            player_runes = next(p for p in runes_info if p['hero_id_'] == player['championId'])

            player['runes'] = []
            for rune_index, rune in enumerate(player_runes['runes_info_']['runes_list_']):
                # slot is 0 for keystones, 1 for first rune of primary tree, ...
                # rank is 1 for most keystones, except stat perks that can be 2
                player['runes'].append({'id': rune['runes_id_'],
                                        'name': lit.get_name(rune['runes_id_'], object_type='rune'),
                                        'slot': rune_index,
                                        'rank': rune['runes_num_']})

            lol_game_dto['teams'][team_side]['players'].append(player)

    return lol_game_dto


def get_game_info(qq_game_id: int):
    game_query_url = f"{endpoints['qq']['match_info']}{qq_game_id}"

    logging.info(f'Querying {game_query_url}')
    response = requests.get(game_query_url)

    return response.json()['msg']


def get_team_info(qq_server_id, qq_battle_id):
    team_info_url = endpoints['qq']['battle_info'] \
        .replace('BATTLE_ID', str(qq_battle_id)) \
        .replace('WORLD_ID', str(qq_server_id))

    logging.info(f'Querying {team_info_url}')
    response = requests.get(team_info_url)

    return json.loads(response.json()['msg'])['battle_list_'][0]


def get_runes_info(qq_world_id, qq_room_id):
    runes_info_url = endpoints['qq']['runes'] \
        .replace('WORLD_ID', str(qq_world_id)) \
        .replace('ROOM_ID', str(qq_room_id))

    logging.info(f'Querying {runes_info_url}')
    response = requests.get(runes_info_url)

    return json.loads(response.json()['msg'])['hero_list_']


def parse_player_battle_data(player_battle_data: dict):
    return {
        # All stats here are end of game stats, so I don’t include the 'total' in field names
        # We start with the most important fields
        'kills': int(player_battle_data['kill']),
        'deaths': int(player_battle_data['death']),
        'assists': int(player_battle_data['assist']),
        'gold': int(player_battle_data['gold']),
        'CS': int(player_battle_data['lasthit']),
        'level': int(player_battle_data['level']),
        # We cast boolean statistics as proper booleans
        'firstBlood': bool(player_battle_data['firstBlood']),
        'firstTower': bool(player_battle_data['firstTower']),
        # Then we add other numerical statistics
        'killingSprees': int(player_battle_data['killingSprees']),
        'largestKillingSpree': int(player_battle_data['largestKillingSpree']),
        'largestMultiKill': int(player_battle_data['largestMultiKill']),
        'doubleKills': int(player_battle_data['dKills']),
        'tripleKills': int(player_battle_data['tKills']),
        'quadraKills': int(player_battle_data['qKills']),
        'pentaKills': int(player_battle_data['pKills']),
        'towerKills': int(player_battle_data['towerKills']),
        'inhibitorKills': int(player_battle_data['inhibitorKills']),
        'monsterKills': int(player_battle_data['neutralKilled']),
        'monstersKillsInAlliedJungle': int(player_battle_data['neutralKilledTJungle']),
        'monstersKillsInEnemyJungle': int(player_battle_data['neutralKilledEJungle']),
        'wardsPlaced': int(player_battle_data['wardsPlaced']),
        'wardsKilled': int(player_battle_data['wardsKilled']),
        'visionWardsBought': int(player_battle_data['visionWardsBought']),
        'timeDead': int(player_battle_data['deadTime']),
        'largestCriticalStrike': int(player_battle_data['largestCriticalStrike']),
        # Damage totals, using a nomenclature close to match-v4
        'totalDamageDealt': int(player_battle_data['totalDamage']),
        'physicalDamageDealt': int(player_battle_data['pDamageDealt']),
        'magicalDamageDealt': int(player_battle_data['mDamageDealt']),
        'totalDamageDealtToChampions': int(player_battle_data['totalDamageToChamp']),
        'physicalDamageDealtToChampions': int(player_battle_data['pDamageToChamp']),
        'magicalDamageDealtToChampions': int(player_battle_data['mDamageDealtToChamp']),
        'totalDamageTaken': int(player_battle_data['totalDamageTaken']),
        'physicalDamageTaken': int(player_battle_data['pDamageTaken']),
        'magicalDamageTaken': int(player_battle_data['mDamageTaken']),
        'totalHeal': int(player_battle_data['totalHeal']),
        # This is the raw player name in the game
        'inGameName': player_battle_data['name'],
        # Each field with an id will be translated in a similar Name object.
        'championId': int(player_battle_data['hero']),
        'championName': lit.get_name(player_battle_data['hero'], object_type='champion'),
        # Summoner spells are a list ordered as D -> F summoner spell
        'summonerSpells': [{'id': int(player_battle_data[skill_key]),
                            'name': lit.get_name(player_battle_data[skill_key],
                                                 object_type='summoner_spell'),
                            'slot': int(skill_key[-1])}
                           for skill_key in ['skill-1', 'skill-2']],
        # Items are also a list with ID, name, and slot
        'items': [{'id': int(player_battle_data['equip'][key]),
                   'name': lit.get_name(player_battle_data['equip'][key], object_type='item'),
                   'slot': int(key[-1])}
                  for key in player_battle_data['equip']]
    }

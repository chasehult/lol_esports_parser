import json

import pytest
from leaguepedia_esports_parser.qq_parser import get_qq_series_dto, get_game_info, parse_player


@pytest.fixture
def game_info():
    return get_game_info('5346')


def test_get_game_info(game_info):
    assert game_info['sMatchId'] == '5346'


def test_parse_player(game_info):
    battle_data = json.loads(game_info['battleInfo']['BattleData'])
    duke_info = battle_data['left']['players'][0]

    duke = parse_player(duke_info, 'red')

    assert duke['kills'] == 4
    assert duke['totalCS'] == 237


def test_lpl_finals():
    match_url = 'http://lol.qq.com/match/match_data.shtml?bmid=6131'

    series = get_qq_series_dto(match_url)

    assert series['winner'] == 'JDG'
    assert series['score'] == {'JDG': 3, 'TES': 2}

    game = series['games'][5]

    assert game['duration'] == 1679
    assert game['picksBans'][0]['championName'] == 'Zoe'

    assert game['players'].__len__() == 10

    yagao = next(p for p in game['players'] if p['role'] == 'mid' and p['team'] == 'red')

    assert yagao['kills'] == 4
    assert yagao['totalCS'] == 184
    assert yagao['runes'][0]['name'] == 'Fleet Footwork'

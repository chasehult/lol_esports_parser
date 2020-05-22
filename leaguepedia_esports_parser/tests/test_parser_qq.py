import json
import pytest
from leaguepedia_esports_parser.qq_parser import get_qq_series_dto, get_game_info, parse_player_battle_data


@pytest.fixture
def game_info():
    return get_game_info(5346)


def test_get_game_info(game_info):
    assert game_info['sMatchId'] == '5346'


def test_parse_player(game_info):
    battle_data = json.loads(game_info['battleInfo']['BattleData'])
    duke_info = battle_data['left']['players'][0]

    duke = parse_player_battle_data(duke_info)

    assert duke['inGameName'] == 'IGDuke'
    assert duke['kills'] == 4
    assert duke['CS'] == 237


def test_lpl_finals():
    match_url = 'http://lol.qq.com/match/match_data.shtml?bmid=6131'

    series = get_qq_series_dto(match_url)

    assert series['winner'] == 'JDG'
    assert series['score'] == {'JDG': 3, 'TES': 2}

    game = series['games'][4]

    assert game['duration'] == 1679

    assert game['teams']['blue']['players'].__len__() == 5

    yagao = next(p for p in game['teams']['red']['players'] if p['role'] == 'mid')

    assert yagao['inGameName'] == 'JDGYagao'
    assert yagao['kills'] == 4
    assert yagao['CS'] == 184
    assert yagao['runes'][0]['name'] == 'Fleet Footwork'

    # TODO Add bans information
    # assert game['picksBans'][0]['championName'] == 'Zoe'

##


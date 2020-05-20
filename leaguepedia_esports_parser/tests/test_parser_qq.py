import pytest
from leaguepedia_esports_parser.qq_parser import get_all_games_dto, get_game_info


@pytest.fixture
def game_info():
    return get_game_info(5346)


def test_get_game_info(game_info):
    assert int(game_info['sMatchId']) == 5346


def test_lpl_finals():
    match_url = 'http://lol.qq.com/match/match_data.shtml?bmid=6131'

    dto_list = get_all_games_dto(match_url)

    lol_game_name_dto = dto_list[4]

    assert lol_game_name_dto['duration'] == 1679
    assert lol_game_name_dto['picks_bans'][0]['champion_name'] == 'Zoe'

    assert lol_game_name_dto['players'].__len__() == 10

    yagao = next(p for p in lol_game_name_dto['players'] if p['role'] == 'mid' and p['team'] == 'red')

    assert yagao['kills'] == 4
    assert yagao['total_cs'] == 184
    assert yagao['runes']['keystone_name'] == 'Fleet Footwork'

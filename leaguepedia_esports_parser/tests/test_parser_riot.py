from leaguepedia_esports_parser.riot_parser import get_game_dto


def test_lck_finals():
    mh_url = 'https://matchhistory.na.leagueoflegends.com/en/#match-details/' \
             'ESPORTSTMNT03/1353193?gameHash=63e4e6e5d695f410'

    lol_game_name_dto = get_game_dto(mh_url, True, True)

    assert lol_game_name_dto['duration'] == 1776
    assert lol_game_name_dto['picks_bans'][0]['champion_name'] == 'LeBlanc'

    assert lol_game_name_dto['players'].__len__() == 10

    faker = next(p for p in lol_game_name_dto['players'] if p['role'] == 'mid' and p['team'] == 'red')

    assert faker['kills'] == 3
    assert faker['total_cs'] == 242
    assert faker['runes']['keystone_name'] == 'Lethal Tempo'

from lol_esports_parser.acs.riot_parser import get_acs_game


def test_lck_finals():
    mh_url = 'https://matchhistory.na.leagueoflegends.com/en/#match-details/' \
             'ESPORTSTMNT03/1353193?gameHash=63e4e6e5d695f410'

    lol_game_name_dto = get_acs_game(mh_url, True, True)

    assert lol_game_name_dto['duration'] == 1776

    # TODO Define 'picks_bans' properly
    # assert lol_game_name_dto['picks_bans'][0]['championName'] == 'LeBlanc'

    assert lol_game_name_dto['teams']['BLUE']['players'].__len__() == 5

    faker = next(p for p in lol_game_name_dto['teams']['RED']['players'] if p['inGameName'] == 'T1 Faker')

    assert faker['championName'] == 'Azir'
    assert faker['endOfGameStats']['kills'] == 3
    assert faker['endOfGameStats']['cs'] == 242
    assert faker['runes'][0]['name'] == 'Lethal Tempo'

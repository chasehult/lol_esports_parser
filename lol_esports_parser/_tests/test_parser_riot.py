import json
import os

from lol_esports_parser.parsers.acs.acs_parser import get_acs_game, get_acs_series


def test_lck_finals():
    mh_urls = [
        "http://matchhistory.na.leagueoflegends.com/en/#match-details/ESPORTSTMNT03/1343103?gameHash=3be9aa065988f4ba",
        "http://matchhistory.na.leagueoflegends.com/en/#match-details/ESPORTSTMNT03/1353189?gameHash=1fd02efc67644051",
        "http://matchhistory.na.leagueoflegends.com/en/#match-details/ESPORTSTMNT03/1353193?gameHash=63e4e6e5d695f410",
    ]

    lck_finals = get_acs_series(mh_urls, get_timeline=True, add_names=True)

    with open(os.path.join("json_examples", "lck_series.json"), "w+") as file:
        json.dump(lck_finals, file, indent=4)

    assert lck_finals['score'] == {'T1': 3, 'GEN': 0}
    assert lck_finals['winner'] == 'T1'


def test_lck_finals_game_3():
    mh_url = (
        "https://matchhistory.na.leagueoflegends.com/en/#match-details/ESPORTSTMNT03/1353193?gameHash=63e4e6e5d695f410"
    )

    game = get_acs_game(mh_url, get_timeline=True, add_names=True)

    with open(os.path.join("json_examples", "lck_game.json"), "w+") as file:
        json.dump(game, file, indent=4)

    assert game["duration"] == 1776
    assert game["teams"]["BLUE"]["players"].__len__() == 5

    faker = next(p for p in game["teams"]["RED"]["players"] if p["inGameName"] == "T1 Faker")

    assert faker["championName"] == "Azir"
    assert faker["endOfGameStats"]["kills"] == 3
    assert faker["endOfGameStats"]["cs"] == 242
    assert faker["runes"][0]["name"] == "Lethal Tempo"

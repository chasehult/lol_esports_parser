import json
import os

from lol_esports_parser.parsers.acs.acs_parser import get_acs_game


def test_lck_finals():
    mh_url = (
        "https://matchhistory.na.leagueoflegends.com/en/#match-details/"
        "ESPORTSTMNT03/1353193?gameHash=63e4e6e5d695f410"
    )

    game = get_acs_game(mh_url, True, True)

    with open(os.path.join("json_examples", "lck_game.json"), "w+") as file:
        json.dump(game, file, indent=4)

    assert game["duration"] == 1776
    assert game["teams"]["BLUE"]["players"].__len__() == 5

    faker = next(p for p in game["teams"]["RED"]["players"] if p["inGameName"] == "T1 Faker")

    assert faker["championName"] == "Azir"
    assert faker["endOfGameStats"]["kills"] == 3
    assert faker["endOfGameStats"]["cs"] == 242
    assert faker["runes"][0]["name"] == "Lethal Tempo"

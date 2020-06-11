import json
import pytest
import os

from lol_esports_parser.parsers.qq.qq_parser import parse_player_battle_data, get_qq_series_dto
from lol_esports_parser.parsers.qq.qq_access import get_basic_qq_game_info


@pytest.fixture
def game_info():
    return get_basic_qq_game_info(5346)


def test_get_game_info(game_info):
    assert game_info["sMatchId"] == "5346"


def test_parse_player(game_info):
    battle_data = json.loads(game_info["battleInfo"]["BattleData"])
    duke_info = battle_data["left"]["players"][0]

    duke = parse_player_battle_data(duke_info)

    assert duke["inGameName"] == "IGDuke"
    assert duke["endOfGameStats"]["kills"] == 4
    assert duke["endOfGameStats"]["cs"] == 237


def test_lpl_finals():
    match_url = "http://lol.qq.com/match/match_data.shtml?bmid=6131"

    series = get_qq_series_dto(match_url)

    with open(os.path.join("json_examples", "qq_series.json"), "w+") as file:
        json.dump(series, file, indent=4)

    assert series["winner"] == "JDG"
    assert series["score"] == {"JDG": 3, "TES": 2}

    game = series["games"][4]

    assert game["duration"] == 1679

    assert game["teams"]["BLUE"]["players"].__len__() == 5

    yagao = next(p for p in game["teams"]["RED"]["players"] if p["inGameName"] == "JDGYagao")

    assert yagao["endOfGameStats"]["kills"] == 4
    assert yagao["endOfGameStats"]["cs"] == 184
    assert yagao["runes"][0]["name"] == "Fleet Footwork"

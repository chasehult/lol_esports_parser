import json
import logging
import os

import lol_esports_parser


def test_lpl_spring_finals():
    # Standard, working game
    match_url = "http://lol.qq.com/match/match_data.shtml?bmid=6131"

    series = lol_esports_parser.get_qq_series(match_url, "10.7")

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
    assert yagao["primaryRuneTreeName"] == "Precision"


def test_missing_fields():
    # This series’s game 3 is missing many fields
    match_url = "https://lpl.qq.com/es/stats.shtml?bmid=6207"

    series = lol_esports_parser.get_qq_series(match_url, "10.11")

    assert series["winner"] == "LGD"


def test_missing_team_info(caplog):
    # This game’s "team info" returns empty information
    match_url = "https://lpl.qq.com/es/stats.shtml?bmid=5658"

    with caplog.at_level(logging.WARNING):
        series = lol_esports_parser.get_qq_series(match_url, "10.1")
        assert len(caplog.records) > 0

    assert series["winner"] == "JDG"


def test_incoherent_team_data(caplog):
    # This game’s searchMatchInfo and query_battle_info_by_battle_id have incoherent information
    match_url = "https://lpl.qq.com/es/stats.shtml?bmid=6001"

    with caplog.at_level(logging.WARNING):
        series = lol_esports_parser.get_qq_series(match_url, "10.1")
        assert len(caplog.records) > 0

    assert series["winner"] == "WE"


def test_incoherent_player_data(caplog):
    match_url = "https://lpl.qq.com/es/stats.shtml?bmid=6067"

    with caplog.at_level(logging.WARNING):
        series = lol_esports_parser.get_qq_series(match_url, "10.1")
        assert len(caplog.records) > 0

    assert series["winner"] == "JDG"


def test_missing_battle_data(caplog):
    match_url = "https://lpl.qq.com/es/stats.shtml?bmid=6050"

    with caplog.at_level(logging.WARNING):
        series = lol_esports_parser.get_qq_series(match_url, "10.6")
        assert len(caplog.records) > 0

    assert series["winner"] == "RW"


def test_missing_players(caplog):
    match_url = "https://lpl.qq.com/es/stats.shtml?bmid=6062"

    with caplog.at_level(logging.WARNING):
        series = lol_esports_parser.get_qq_series(match_url, "10.6")
        assert len(caplog.records) > 0

    assert series["winner"] == "RW"


def test_missing_less_players(caplog):
    match_url = "https://lpl.qq.com/es/stats.shtml?bmid=6096"

    with caplog.at_level(logging.WARNING):
        series = lol_esports_parser.get_qq_series(match_url, "10.6")
        assert len(caplog.records) > 0

    assert series["winner"] == "WE"
    assert series["score"] == {"WE": 2, "EDG": 1}


def test_wrong_sides(caplog):
    match_url = "https://lpl.qq.com/es/stats.shtml?bmid=6001"

    with caplog.at_level(logging.WARNING):
        series = lol_esports_parser.get_qq_series(match_url, "10.6")
        assert len(caplog.records) > 0

    assert series["winner"] == "WE"

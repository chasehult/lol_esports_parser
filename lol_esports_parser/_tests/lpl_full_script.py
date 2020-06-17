from concurrent.futures.thread import ThreadPoolExecutor
from leaguepedia_parser import LeaguepediaParser

from lol_esports_parser.parsers.acs.acs_parser import get_acs_game
from lol_esports_parser.parsers.qq.qq_parser import get_qq_series_dto

logger.setLevel(logging.INFO)
lp = LeaguepediaParser()

##
lpl = lp.get_tournaments("China", 2019, tournament_level="Primary")
results = {}

loaded_series = set()

with ThreadPoolExecutor() as executor:
    for tournament in lpl:
        games = lp.get_games(tournament["name"])

        for game in games:
            if game["match_history_url"] not in loaded_series:
                print(f'Loading series {game["match_history_url"]}')

                loaded_series.add(game["match_history_url"])

                results[game["match_history_url"]] = {
                    "result": executor.submit(get_qq_series_dto, game["match_history_url"], add_names=False),
                    "games": [game],
                }
            else:
                results[game["match_history_url"]]["games"].append(game)

##
for mh_url in results:
    try:
        series = results[mh_url]["result"].result()
    except StopIteration:
        print(f"Stop iteration: {mh_url}")
        continue

    for idx, game in enumerate(results[mh_url]["games"]):
        lol_game = series["games"][idx]

        leaguepedia_winner = "BLUE" if game["winner"] == "1" else "RED"

        assert lol_game["winner"] == leaguepedia_winner

##
lck = lp.get_tournaments("Korea", 2020, tournament_level="Primary")
results = {}

loaded_series = set()

with ThreadPoolExecutor() as executor:
    for tournament in lck:
        games = lp.get_games(tournament["name"])

        for game in games:
            results[game["match_history_url"]] = {
                "result": executor.submit(get_acs_game, game["match_history_url"]),
                "game": game,
            }

##
for mh_url in results:
    leaguepedia_game = results[mh_url]["game"]

    try:
        lol_game = results[mh_url]["result"].result()
    except:
        print(mh_url)
        continue

    leaguepedia_winner = "BLUE" if leaguepedia_game["winner"] == "1" else "RED"

    assert leaguepedia_winner == lol_game["winner"]

##

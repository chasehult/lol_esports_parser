from typing import TypedDict, List, Dict
from collections import Counter
import lol_dto


class LolSeries(TypedDict):
    """A dictionary representing a League of Legends series (Bo1, Bo3, ...)
    """

    games: List[lol_dto.classes.game.LolGame]  # Individual game objects, sorted by date

    winner: str  # Name of the winning team

    score: Dict[str, int]  # {'team_name': score}


def create_series(games: List[lol_dto.classes.game.LolGame]) -> LolSeries:
    """Creates a LolSeries from a list of LolGame.
    """
    # Making extra sure they’re in the right order
    games = sorted(games, key=lambda x: x["start"])

    # We get the team names from the first game
    team_scores = Counter()

    for lol_game_dto in games:
        for team_side, team in lol_game_dto["teams"].items():
            if lol_game_dto["winner"] == team_side:
                team_scores[team["name"]] += 1
            else:  # Required to make sure teams with no game win still appear
                team_scores[team["name"]] += 0

    return LolSeries(score=dict(team_scores), winner=team_scores.most_common(1)[0][0], games=games)

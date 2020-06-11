from typing import TypedDict, List, Dict

import lol_dto


class LolSeries(TypedDict):
    """A dictionary representing a League of Legends series (Bo1, Bo3, ...)
    """

    games: List[lol_dto.classes.game.LolGame]  # Individual game objects, sorted by date

    winner: str  # Name of the winning team

    score: Dict[str, int]  # {'team_name': score}

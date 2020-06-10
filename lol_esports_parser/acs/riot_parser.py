import urllib.parse
import lol_dto
import riot_transmute

from lol_esports_parser.acs.acs import ACS

acs = ACS()


def get_acs_game(mh_url: str, get_timeline: bool = False, add_names: bool = False) -> lol_dto.classes.game.LolGame:
    """Returns a LolGame for the given match history URL.

    Params:
        mh_url: a Riot match history URL, containing the game hash.
        get_timeline: whether to retrieve the timeline object and merge it in a single LolGame.
        add_names: whether to add objects names for human readability.
    """
    parsed_url = urllib.parse.urlparse(urllib.parse.urlparse(mh_url).fragment)
    query = urllib.parse.parse_qs(parsed_url.query)

    server, game_id = parsed_url.path.split('/')[1:]
    game_hash = query['gameHash'][0]

    match_dto = acs.get_game(server, game_id, game_hash)

    if get_timeline:
        # TODO Get timeline
        pass

    game = riot_transmute.match_to_game(match_dto, add_names=add_names)

    return game

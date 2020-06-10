
def get_game_dto(match_history_url: str, get_timeline=False, add_names=False):
    """Returns the parsed LolGameDto of the game.

    Args:
        match_history_url: the url to parse, pointing to a Riot or QQ endpoint
        get_timeline: whether or not to query the timeline to gather more data
        add_names: whether to keep object IDs or to translate them to English names

    Returns:
        A LolGameDto.
    """
    pass

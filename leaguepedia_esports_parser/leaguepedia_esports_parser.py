
def get_game_dto(url: str, get_additional_data=False, translate_ids=False):
    """Returns the parsed DTO of the game.

    Args:
        url: the url to parse, pointing to a Riot or QQ endpoint
        get_additional_data: whether or not to query other existing endpoints to gather more data
        translate_ids: whether to keep object IDs or to translate them to English names

    Returns:
        A LolGameDto.
    """
    pass

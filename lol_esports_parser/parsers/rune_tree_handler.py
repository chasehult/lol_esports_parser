import warnings
from typing import Tuple
import requests
import lol_dto
import lol_id_tools


class RuneTreeHandler:
    """A simple class that caches data from ddragon and gets rune tree per rune ID.
    """

    def __init__(self):
        self.cache = {}
        self.versions = None
        self.reload_versions()

    def reload_versions(self):
        self.versions = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()

    def get_runes_data(self, patch):
        full_patch = self.get_version(patch)

        if full_patch not in self.cache:
            self.cache[full_patch] = requests.get(
                f"https://ddragon.leagueoflegends.com/cdn/{full_patch}/data/en_US/runesReforged.json"
            ).json()

        return self.cache[full_patch]

    def get_version(self, patch):
        """Returns the game version as defined by ddragon

        Params:
            patch: MM.mm format patch
        """
        for version in self.versions:
            if ".".join(version.split(".")[:2]) == patch:
                return version

        # If we have a patch that we do not know, we reload versions stupidly.
        warnings.warn("Reloading game versions")
        self.reload_versions()
        return self.get_version(patch)

    def get_primary_tree(self, runes, patch) -> Tuple[int, str]:
        return self.get_tree(runes[0], patch)

    def get_secondary_tree(self, runes, patch) -> Tuple[int, str]:
        return self.get_tree(runes[4], patch)

    def get_tree(self, _rune: lol_dto.classes.game.LolGamePlayerRune, patch) -> Tuple[int, str]:
        data = self.get_runes_data(patch)

        for tree in data:
            for slot in tree["slots"]:
                for rune in slot["runes"]:
                    if rune["id"] == _rune["id"]:
                        return tree["id"], lol_id_tools.get_name(tree["id"])

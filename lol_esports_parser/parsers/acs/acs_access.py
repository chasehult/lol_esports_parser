import logging
import time
from json import JSONDecodeError

import requests

from lol_esports_parser.config import credentials, endpoints, credentials_location


class ACS:
    """Class handling connecting and retrieving games from ACS endpoints.
    """

    data = {
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": "eyJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJodHRwczpcL1wvYXV0aC5yaW90Z2FtZXMuY29tXC90b2tlbiIsInN1YiI6ImxvbCIsImlzcyI6ImxvbCIsImV4cCI6MTYwMTE1MTIxNCwiaWF0IjoxNTM4MDc5MjE0LCJqdGkiOiIwYzY3OThmNi05YTgyLTQwY2ItOWViOC1lZTY5NjJhOGUyZDcifQ.dfPcFQr4VTZpv8yl1IDKWZz06yy049ANaLt-AKoQ53GpJrdITU3iEUcdfibAh1qFEpvVqWFaUAKbVIxQotT1QvYBgo_bohJkAPJnZa5v0-vHaXysyOHqB9dXrL6CKdn_QtoxjH2k58ZgxGeW6Xsd0kljjDiD4Z0CRR_FW8OVdFoUYh31SX0HidOs1BLBOp6GnJTWh--dcptgJ1ixUBjoXWC1cgEWYfV00-DNsTwer0UI4YN2TDmmSifAtWou3lMbqmiQIsIHaRuDlcZbNEv_b6XuzUhi_lRzYCwE4IKSR-AwX_8mLNBLTVb8QzIJCPR-MGaPL8hKPdprgjxT0m96gw",
        "grant_type": "password",
        "username": credentials["account_name"],
        "password": credentials["password"],
        "scope": "openid offline_access lol ban profile email phone",
    }

    def __init__(self, retry_once=True):
        self.session = requests.Session()
        self.token = self.get_token()
        self.base_url = endpoints["acs"]["game"]
        self.retry_once = retry_once

    def get_token(self, first_try=True):
        try:
            token_request = self.session.post("https://auth.riotgames.com/token", data=self.data)
            return token_request.json()["id_token"]
        except JSONDecodeError:
            if self.retry_once and first_try:
                return self.get_token(False)

            logging.warning(f"Could not acquire ID token for user {credentials['account_name']}")
            logging.warning(f"Please make sure your credentials at {credentials_location} are right")
            return None

    def _get_from_api(self, uri, first_try=True):
        request_url = f"{self.base_url}{uri}"
        logging.debug("Making a call to: " + request_url)

        response = self.session.get(request_url, cookies={"id_token": self.token})

        if response.status_code != 200:
            if self.retry_once and first_try:
                time.sleep(1)
                return self._get_from_api(uri, False)

            logging.error("Status code %d", response.status_code)
            logging.error("Headers: %s", response.headers)
            logging.error("Resp: %s", response.text)
            raise requests.HTTPError

        return response.json()

    def get_game(self, server, game_id, game_hash):
        return self._get_from_api(f"{server}/{game_id}?gameHash={game_hash}")

    def get_game_timeline(self, server, game_id, game_hash):
        return self._get_from_api(f"{server}/{game_id}/timeline?gameHash={game_hash}")

import json
import os

config_folder = os.path.join(os.path.expanduser("~"), ".config", "lol_esports_parser")
endpoints_location = os.path.join(config_folder, "endpoints.json")
credentials_location = os.path.join(config_folder, "credentials.json")

if not os.path.exists(config_folder):
    os.makedirs(config_folder)
    raise FileNotFoundError(f"Please create {endpoints_location}.")

with open(endpoints_location) as file:
    endpoints = json.load(file)

if not os.path.exists(credentials_location):
    print(
        f"Creating {credentials_location} locally.\n"
        "This information is required to connect to the ACS endpoints.\n"
        f"Password will be saved in clear, so make sure only your user has read access on the file.\n"
    )
    account_name = input("Please input your LoL account name:")
    password = input("Please input your LoL account password:")

    with open(credentials_location, "w+") as file:
        json.dump({"account_name": account_name, "password": password}, file, indent=4)

with open(credentials_location) as file:
    credentials = json.load(file)

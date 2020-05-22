import json
import os

config_folder = os.path.join(os.path.expanduser('~'), '.config', 'leaguepedia')
endpoints_location = os.path.join(config_folder, 'endpoints.json')

if not os.path.exists(config_folder):
    os.makedirs(config_folder)
    raise FileNotFoundError(f'Please create {endpoints_location}.')

with open(endpoints_location) as file:
    endpoints = json.load(file)

roles_list = ['top', 'jungle', 'mid', 'bot', 'support']

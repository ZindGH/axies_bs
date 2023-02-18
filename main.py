import requests
import json
from credentials import api_token

def get_leaderboard(number_of_places : int=100, first_rank : int=0):
    """

    :param number_of_places: number of ranks to be returned
    :param first_rank: rank offset
    :return: list of tuples ('userID', 'rank')
    """
    url = "https://api-gateway.skymavis.com/origin/v2/leaderboards"
    headers = {
        "accept": "application/json",
        "X-API-Key": api_token
    }
    params = {
        'limit': number_of_places,
        'offset': first_rank
    }
    r = requests.get(url, headers=headers, params=params )
    leaders = json.loads(r.text)['_items']
    return [(leader['userID'], leader['topRank']) for leader in leaders]

def get_axie_list(userid: str, number_of_games):
    url = 'https://api-gateway.skymavis.com/x/origin/battle-history'
    headers = {
        "accept": "application/json",
        "X-API-Key": api_token
    }
    params = {
        'client_id': userid,
        'type': 'pvp',
        'limit': number_of_games,
    }
    r = requests.get(url, headers=headers, params=params)
    battles = json.loads(r.text)['battles']
    match = 0
    for battle in battles:
        
        if match == 3:
            break
    return axies
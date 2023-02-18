import requests
import json
from credentials import api_token
import logging

logging.basicConfig(level=logging.DEBUG, filename='logs.log', format='%(asctime)s :: %(levelname)s :: %(message)s')


def get_leaderboard(number_of_places: int = 100, first_rank: int = 0):
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
    r = requests.get(url, headers=headers, params=params)
    leaders = json.loads(r.text)['_items']
    logging.debug(f'get_leaderboard\nstatus_code: {r.status_code}')
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
    for battle in battles:
        if battle['client_ids'][0] == userid:
            axie_team = battle['first_client_fighters']
        else:
            axie_team = battle['second_client_fighters']
        axie_ids = [axie['axie_id'] for axie in axie_team]
    logging.info(f'axie_ids: {axie_ids}')
    return axie_ids


if __name__ == '__main__':
    user_ids = get_leaderboard(first_rank=1000, number_of_places=10)
    for user_id in user_ids:
        get_axie_list(number_of_games=3, userid=user_id)

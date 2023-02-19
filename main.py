import requests
import json
from credentials import api_token
import logging
from agp_py import AxieGene

logging.basicConfig(level=logging.DEBUG, filename='logs.log', format='%(asctime)s :: %(levelname)s :: %(message)s')
marketplace_endpoint = 'https://graphql-gateway.axieinfinity.com/graphql/'
parts = ['eyes', 'mouth', 'ears', 'horn', 'back', 'tail']

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


def get_axie_list(userid: str, number_of_games: int = 1):
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
    axie_info = [(axie['axie_id'], axie['gene']) for axie in axie_team]  # Just take last battle to explore
    logging.info(f'axie_info: {axie_info}')
    return axie_info

def retrieve_data_from_gene(axie_info, hex_type: int = 512):
    """
    Retrieves information from gene string.

    :param axie_info: list of tuples (id, gene)
    :param hex_type: int: 256 or 512
    :return: dictionary with class and axie parts
    """
    axies = list()
    for axie_id, gene_hex in axie_info:
        axie = dict()
        gene = AxieGene(hex_string=gene_hex, hex_type=hex_type)
        parts = ['eyes', 'mouth', 'ears', 'horn', 'back', 'tail']
        axie['class'] = gene.genes['cls'].capitalize()
        axie['id'] = axie_id
        for part in parts:
            axie[part] = gene.genes[part]['d']['partId']
    axies.append(axie)
    return axies

def get_similar_axies(axie_detail):
    """Get twin axies

    :param axie_detail: dictionary with axie class and parts
    :return: list with twin axies
    """
    part_ids = [axie_detail.get(key) for key in parts]
    query = {
        "operationName": "GetAxieBriefList",
        "variables": {
            "from": 0,
            "size": 24,
            "sort": "PriceAsc",
            "auctionType": "Sale",
            "criteria": {
                'parts': part_ids,
                'classes': axie_detail['class']
            }
        },
        "query": "query GetAxieBriefList($auctionType: AuctionType, $criteria: AxieSearchCriteria, $from: Int, $sort: SortBy, $size: Int, $owner: String) {\n  axies(\n    auctionType: $auctionType\n    criteria: $criteria\n    from: $from\n    sort: $sort\n    size: $size\n    owner: $owner\n  ) {\n    total\n    results {\n      ...AxieBrief\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment AxieBrief on Axie {\n  id\n  name\n  stage\n  class\n  breedCount\n  image\n  title\n  genes\n  newGenes\n  battleInfo {\n    banned\n    __typename\n  }\n  order {\n    id\n    currentPrice\n    currentPriceUsd\n    __typename\n  }\n  parts {\n    id\n    name\n    class\n    type\n    specialGenes\n    __typename\n  }\n  __typename\n}\n"
    }
    r = requests.post(url=marketplace_endpoint,
                      json=query,
                      headers={'content-type': 'application/json'})
    similar_axies_raw = json.loads(r.text)
    if similar_axies_raw['data']['axies']['total'] == 0:
        return None
    else:
        return similar_axies_raw['data']['axies']['results']


if __name__ == '__main__':
    user_ids = get_leaderboard(first_rank=1000, number_of_places=1)
    for user_id in user_ids:
        axie_info = get_axie_list(number_of_games=3, userid=user_id)
    axies = retrieve_data_from_gene(axie_info)
    get_similar_axies(axies[0])

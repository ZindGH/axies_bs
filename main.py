import pandas as pd
import requests
import json
import pandas
from credentials import api_token
import logging
from agp_py import AxieGene

logging.basicConfig(level=logging.INFO, filename='logs.log', format='%(asctime)s :: %(levelname)s :: %(message)s')
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
    logging.debug(f'get_leaderboard\nstatus_code: {r.status_code}')
    leaders = json.loads(r.text)['_items']
    return [(leader['userID'], leader['topRank']) for leader in leaders]


def get_axie_list(userid: str, number_of_games: int = 1):
    """ Get list of last battle axies

    :param userid:
    :param number_of_games: not implemented
    :return: return axieID and gene
    """
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
    battles_match_ids, battle_genes = dict(), dict()
    for battle in battles:
        if battle['client_ids'][0] == userid:
            axie_team = battle['first_client_fighters']
        else:
            axie_team = battle['second_client_fighters']
        for axie in axie_team:
            battles_match_ids[axie['axie_id']] = battles_match_ids.get(axie['axie_id'], 0) + 1
            battle_genes[axie['axie_id']] = battle_genes.get(axie['axie_id'], axie['gene'])
        top_ids = dict(sorted(battles_match_ids.items(), key=lambda x: x[1], reverse=True)[0:3]).keys()

    # axie_info = [(axie['axie_id'], axie['gene']) for axie in axie_team]  # Just take last battle to explore
    axie_info = [(axie_id, str(battle_genes[axie_id])) for axie_id in top_ids]
    logging.debug(f'axie_info: {axie_info}')
    return axie_info

def retrieve_data_from_gene(axie_info, hex_type: int = 512):
    """
    Retrieves information from gene string.

    :param axie_info: list of tuples (id, gene)
    :param hex_type: int: 256 or 512
    :return: list of dictionaries with class and axie parts [{'class', 'eye'...}
    """
    axies = list()
    parts = ['eyes', 'mouth', 'ears', 'horn', 'back', 'tail']
    for axie_id, gene_hex in axie_info:
        axie = dict()
        try:
            gene = AxieGene(hex_string=gene_hex, hex_type=hex_type)
        except KeyError:
            logging.debug(f'id({axie_id}): gene KeyError')
            return None
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
    if r.status_code != 200:
        logging.info(f'get_similar_axies status_code: {r.status_code}')
        return None
    similar_axies_raw = json.loads(r.text)
    if similar_axies_raw['data']['axies']['total'] == 0:
        logging.debug(f"No twin axies acessible on marketplace for id: {axie_detail.get('id', 'ID not given.')}")
        return None
    else:
        return similar_axies_raw['data']['axies']['results']

def get_axie_info_from_twins(axie):  # Not used
    """Return axie info from (get_similar_axies)

    :param axie: in list
    :return: dictionary with axie {id, class, price}
    """
    axie_info = dict()
    axie_info['id'] = axie['id']
    axie_info['class'] = axie['class']
    axie_info['price'] = round(float(axie['order']['currentPriceUsd'], decimal=1))
    return axie_info  #
def get_cheapest_axie_from_twins(axies):
    """Get cheapest axie from twins

    :param axies: list of dictionaries {id, orders}
    :return: pandas DataFrame({id, order_currentPriceUsd})
    """
    if axies is None:
        return None
    df_axies = pd.json_normalize(axies, sep='_')
    df_axies = df_axies[df_axies.order_currentPriceUsd == df_axies.order_currentPriceUsd.min()]
    df_axies['order_currentPriceUse'] = df_axies['order_currentPriceUsd']
    return df_axies[['id', 'order_currentPriceUsd']].rename(columns={'order_currentPriceUsd': 'price'})

def team_price(axie_team):
    return sum([axie['price'] for axie in axie_team])  # Not used
def get_cheapest_teams(users, price_range: list = [0, 100000]):
    """

    :param users:
    :param rank_offset:
    :param price_range:
    :return: list of dictionaries (teams) {rank, ids[], price}
    """
    teams_df = pd.DataFrame(columns=['rank', 'id_1', 'id_2', 'id_3', 'price'])
    for user_id, user_rank in users:
        continue_flag = False
        team_info = {'rank': user_rank}
        axies = get_axie_list(user_id)  # Get 3 axies
        axies_parts = retrieve_data_from_gene(axies)  # get parts_info of 3 axies
        if axies_parts is None:
            continue
        sum_price = 0
        for i, axie_parts in enumerate(axies_parts):  # loop through axies
            cheap_axie = get_cheapest_axie_from_twins(get_similar_axies(axie_parts))  # get chepest axie (if exist)
            if not isinstance(cheap_axie, pd.DataFrame):
                continue_flag = True
                break
            team_info[f'id_{i+1}'] = cheap_axie['id'].iloc[0]
            sum_price += float(cheap_axie['price'].iloc[0])
        if continue_flag:
            continue
        team_info['price'] = round(sum_price, 1)
        teams_df = pd.concat([teams_df, pd.DataFrame(team_info, index=[0])], ignore_index=True)
        logging.info('Team_rank:{rank} :: axie_ids:{id_1}|{id_2}|{id_3} :: Price: {price}'.format(**team_info))
    return teams_df
def select_n_cheapest_teams(teams, rank_limit: list = [1, 10000]):
    """ Select N cheapest teams in rank range

    :param teams: DataFrame {rank, ids[], price}
    :param rank_limit: team rank limit [min, max]
    :return: DataFrame {rank, ids[], price}
    """
    # teams = teams[teams['rank'] > rank_limit[0] and teams['rank'] <= rank_limit[1]]
    return teams[(teams['rank'] > rank_limit[0]) and (teams['rank'] <= rank_limit[1])].sort_values(by=['price', 'rank'])

def find_similar_axie_by_id(axie_id):
    """ Get twin axie ids from marketplace by ID

    :param axie_id: axie_id
    :return: list of ids
    """
    axie_info = [axie_id, retrieve_gen_by_id(axie_id)]  # receive gen by id
    axie_parts = retrieve_data_from_gene(axie_info)  # receive parts by gen
    twin_axies = get_similar_axies(axie_parts)  #
    return [twin_axie['id'] for twin_axie['id'] in twin_axies]

def retrieve_gen_by_id(axie_id):
    query = {
        "operationName": "GetAxieDetail",
        "variables": {
            "axieId": axie_id
        },
        "query": "query GetAxieDetail($axieId: ID!) {\n  axie(axieId: $axieId) {\n    ...AxieDetail\n    __typename\n  }\n}\n\nfragment AxieDetail on Axie {\n  id\n  image\n  class\n  chain\n  name\n  genes\n  owner\n  birthDate\n  bodyShape\n  class\n  sireId\n  sireClass\n  matronId\n  matronClass\n  stage\n  title\n  breedCount\n  level\n  figure {\n    atlas\n    model\n    image\n    __typename\n  }\n  parts {\n    ...AxiePart\n    __typename\n  }\n  stats {\n    ...AxieStats\n    __typename\n  }\n  auction {\n    ...AxieAuction\n    __typename\n  }\n  ownerProfile {\n    name\n    __typename\n  }\n  battleInfo {\n    ...AxieBattleInfo\n    __typename\n  }\n  children {\n    id\n    name\n    class\n    image\n    title\n    stage\n    __typename\n  }\n  __typename\n}\n\nfragment AxieBattleInfo on AxieBattleInfo {\n  banned\n  banUntil\n  level\n  __typename\n}\n\nfragment AxiePart on AxiePart {\n  id\n  name\n  class\n  type\n  specialGenes\n  stage\n  abilities {\n    ...AxieCardAbility\n    __typename\n  }\n  __typename\n}\n\nfragment AxieCardAbility on AxieCardAbility {\n  id\n  name\n  attack\n  defense\n  energy\n  description\n  backgroundUrl\n  effectIconUrl\n  __typename\n}\n\nfragment AxieStats on AxieStats {\n  hp\n  speed\n  skill\n  morale\n  __typename\n}\n\nfragment AxieAuction on Auction {\n  startingPrice\n  endingPrice\n  startingTimestamp\n  endingTimestamp\n  duration\n  timeLeft\n  currentPrice\n  currentPriceUSD\n  suggestedPrice\n  seller\n  listingIndex\n  state\n  __typename\n}\n"
    }

    r = requests.post(url=marketplace_endpoint,
                      json=query,
                      headers={'content-type': 'application/json'})
    if r.status_code != 200:
        logging.info(f'get_similar_axies_by_id: status_code: {r.status_code}')
        return None
    axie_gene = json.loads(r.text)['data']['axie']['newGenes']
    return axie_gene
if __name__ == '__main__':
    f_r = 1500
    n_p = 1700
    teams_df = pd.DataFrame(columns=['rank', 'id_1', 'id_2', 'id_3', 'price'])
    for place in range(f_r, n_p, 100):
        user_ids = get_leaderboard(first_rank=place, number_of_places=100)
        teams_banch = get_cheapest_teams(user_ids)
        teams_df = pd.concat([teams_df, teams_banch], ignore_index=True)
    print(teams_df.sort_values(by='price').head())



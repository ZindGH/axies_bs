import cProfile, pstats
import pandas as pd
import requests
import json
import pandas
from credentials import api_token, sample_user_id
import logging
from agp_py import AxieGene
import tools
from collections import Counter

pd.options.mode.chained_assignment = None
logging.basicConfig(level=logging.INFO, filename='logs_rework.log', format='%(asctime)s :: %(levelname)s :: %(message)s')
# tools.erase_log()
marketplace_endpoint = 'https://graphql-gateway.axieinfinity.com/graphql/'
parts = ['eyes', 'mouth', 'ears', 'horn', 'back', 'tail']

class AxieUser:

    def __init__(self, user_id: int = sample_user_id, axie_ids: list = None):
        self.user_id = user_id
        self.axies = self.get_axies(axie_ids=axie_ids)
        self.items = self.get_user_items()
        #  Consuming operations expensive operations
        self.battles = None
        self.active_team = None


    def get_axie_ids(self):
        """ Get user Axie ids

        :return: list of int [id1, id2...], None for error
        """
        url = 'https://api-gateway.skymavis.com/origin/v2/community/users/fighters'
        headers = {
            "accept": "application/json",
            "X-API-Key": api_token
        }
        params = {
            'axieType': 'ronin',
            'userID': self.user_id
        }
        try:
            r = requests.get(url, headers=headers, params=params)
            if r.status_code != 200:
                logging.info(f"get_axies status_code: {r.status_code} || user_id :{self.user_id}")
                return None
        except requests.exceptions.RequestException as error:
                logging.info(f"User id: {self.user_id} Axies can't be accessed due to: {error}.")
        return [axie['id'] for axie in json.loads(r.text)['_items']]

    def get_axies(self, axie_ids: list = None):
        """ Get Axies from axie ids.

        :param axie_ids: list of Axie ids, for None use user_ids
        :return:
        """
        if axie_ids is None:
            return [Axie(axie_id) for axie_id in self.get_axie_ids()]
        elif len(axie_ids) == 0:  # In case of no need of axies
            return None
        else:
            return [Axie(axie_id) for axie_id in axie_ids]


    def get_min_axie_prices(self, axies: list = None):
        """ Get minimum market praces for twin axies

        :param axies: list of axies for price check
        :return: list of dicts {id, id_twin, price} for player axies
        """
        if axies == None:
            axies = self.axies
        out = list()
        for axie in axies:
            twin = axie.get_twins(size=1)
            if twin:
                out.append({'id': axie.axie_id,
                            'id_twin': twin['id'],
                            'price': float(twin['price'])})
            else:
                out.append({'id': axie.axie_id,
                            'id_twin': None,
                            'price': None})
        return out

    def get_battle_history(self, number_of_games: int = 5):
        """ Get list of recent player games

            :param number_of_games: not implemented
            :return: return axieID and gene
            """
        url = 'https://api-gateway.skymavis.com/x/origin/battle-history'
        headers = {
            "accept": "application/json",
            "X-API-Key": api_token
        }
        params = {
            'client_id': self.user_id,
            'type': 'pvp',
            'limit': number_of_games,
        }
        try:
            r = requests.get(url, headers=headers, params=params)
            if r.status_code != 200:
                logging.info(f"Getting list of battle, error: {r.status_code}")
        except requests.exceptions.RequestException as error:
                logging.info(f"User id: {self.user_id}. Battles can't be accessed due to: {error}.")
        self.battles = json.loads(r.text)['battles']
        return self.battles

    @staticmethod
    def get_leaderboard(number_of_places: int = 100, offset: int = 1, request_capacity: int = None):
        """ Get Player ids from leaderboard

           :param number_of_places: number of ranks to be returned
           :param first_rank: rank offset
           :param request_capacity: number of places in one request. if None, request_capasity:
           :return: list of tuples ('userID', 'rank')
           """
        if request_capacity is None:
            if number_of_places >= 100:
                request_capacity = 100
            else:
                request_capacity = number_of_places
        leaders = list()
        url = "https://api-gateway.skymavis.com/origin/v2/leaderboards"
        headers = {
            "accept": "application/json",
            "X-API-Key": api_token
        }
        for batch_of_places in range(offset, offset + number_of_places, request_capacity):
            params = {
                'limit': request_capacity,
                'offset': batch_of_places
            }
            try:
                r = requests.get(url, headers=headers, params=params)
                if r.status_code != 200:
                    logging.info(f"Get leaderboard error: {r.status_code}")
                    return None
            except requests.exceptions.RequestException as error:
                logging.info(f"Leaderboard can't be accessed due to: {error}.")
                return None

            leaders.extend([(leader['topRank'], leader['userID']) for leader in json.loads(r.text)['_items']])
        return leaders


    def get_active_team(self):
        """ Get active team of a player

        :param user_id: player id
        :return: list of Axie instances of an active team for user_id
        """
        battles_match_ids = Counter()
        for battle in self.battles:
            if battle['client_ids'][0] == self.user_id:  # Decide first team or second team
                axie_team = battle['first_client_fighters']
            else:
                axie_team = battle['second_client_fighters']
            for axie in axie_team:  # If 2 teams used in last number_of_games, find with most playable axies.
                battles_match_ids[axie['axie_id']] += 1
        if len(battles_match_ids) == 3:
            self.active_team = [Axie(axie_id) for axie_id in battles_match_ids.keys()]
        else:
            self.active_team = [Axie(ax_id[0]) for ax_id in battles_match_ids.most_common(3)]

        # self.active_team = [Axie(i[0]) for i in sorted(battles_match_ids.items(), key=lambda x: x[1], reverse=True)[0:3]]

        return self.active_team  # Get most popular



    def get_team_price(self):
        """ Get price of an active team

        :return: {price, axie_ids}
        """
        team_info = self.get_min_axie_prices(axies=self.active_team)
        if any(data['price'] is None for data in team_info):  # Check if there is a None value (no twin axie)
            return None
        return {'price': round(sum([axie['price'] for axie in team_info], 2)),
                'twin_id1': team_info[0]['id_twin'],
                'twin_id2': team_info[1]['id_twin'],
                'twin_id3': team_info[2]['id_twin']}


    @staticmethod
    def get_leaderboard_team_prices(number_of_places: int = 100,
                                    offset: int = 1,
                                    request_capacity: int = None,
                                    log_output: bool = False):
        """ Return prices of teams (where twins exist) in a leaderboard

        :param log_output: True if write output in logfile INFO level
        :return: list of dicts {rank, [axie_ids], price}
        """
        leaderboard = AxieUser.get_leaderboard(number_of_places, offset, request_capacity)
        leader_prices = list()
        for rank, user_id in leaderboard:
            user = AxieUser(user_id, axie_ids=[])
            user.leaderboard_update()
            team_info = user.get_team_price()
            if team_info is None:
                continue
            if log_output:
                logging.info(f"Team_rank: {rank} :: axie_ids:"
                             f" {team_info['twin_id1']}|{team_info['twin_id2']}|{team_info['twin_id3']} "
                             f":: Price: {team_info['price']}")
            leader_prices.append({'rank': rank, **team_info})
        return leader_prices

    def leaderboard_update(self):
        self.get_battle_history()
        self.get_active_team()






    def get_user_items(self):

        return

class Axie:
    def __init__(self, axie_id: int):
        self.axie_id = axie_id
        self.axie_genes = self.get_genes()
        self.axie_class, self.axie_parts = self.retrieve_parts_from_genes()
        # Consuming operation
        self.twins = None  # get_twins()

    def get_genes(self):
        """ Get genes from axie_id

        :return: string genes (512 byte)
        """
        query = {
            "operationName": "GetAxieDetail",
            "variables": {
                "axieId": self.axie_id
            },
            "query": "query GetAxieDetail($axieId: ID!) {\n  axie(axieId: $axieId) {\n    ...AxieDetail\n    __typename\n  }\n}\n\nfragment AxieDetail on Axie {\n  id\n  image\n  class\n  chain\n  name\n  genes\n  newGenes\n  owner\n  birthDate\n  bodyShape\n  class\n  sireId\n  sireClass\n  matronId\n  matronClass\n  stage\n  title\n  breedCount\n  level\n  figure {\n    atlas\n    model\n    image\n    __typename\n  }\n  parts {\n    ...AxiePart\n    __typename\n  }\n  stats {\n    ...AxieStats\n    __typename\n  }\n  order {\n    ...OrderInfo\n    __typename\n  }\n  ownerProfile {\n    name\n    __typename\n  }\n  battleInfo {\n    ...AxieBattleInfo\n    __typename\n  }\n  children {\n    id\n    name\n    class\n    image\n    title\n    stage\n    __typename\n  }\n  potentialPoints {\n    beast\n    aquatic\n    plant\n    bug\n    bird\n    reptile\n    mech\n    dawn\n    dusk\n    __typename\n  }\n  equipmentInstances {\n    ...EquipmentInstance\n    __typename\n  }\n  __typename\n}\n\nfragment AxieBattleInfo on AxieBattleInfo {\n  banned\n  banUntil\n  level\n  __typename\n}\n\nfragment AxiePart on AxiePart {\n  id\n  name\n  class\n  type\n  specialGenes\n  stage\n  abilities {\n    ...AxieCardAbility\n    __typename\n  }\n  __typename\n}\n\nfragment AxieCardAbility on AxieCardAbility {\n  id\n  name\n  attack\n  defense\n  energy\n  description\n  backgroundUrl\n  effectIconUrl\n  __typename\n}\n\nfragment AxieStats on AxieStats {\n  hp\n  speed\n  skill\n  morale\n  __typename\n}\n\nfragment OrderInfo on Order {\n  id\n  maker\n  kind\n  assets {\n    ...AssetInfo\n    __typename\n  }\n  expiredAt\n  paymentToken\n  startedAt\n  basePrice\n  endedAt\n  endedPrice\n  expectedState\n  nonce\n  marketFeePercentage\n  signature\n  hash\n  duration\n  timeLeft\n  currentPrice\n  suggestedPrice\n  currentPriceUsd\n  __typename\n}\n\nfragment AssetInfo on Asset {\n  erc\n  address\n  id\n  quantity\n  orderId\n  __typename\n}\n\nfragment EquipmentInstance on EquipmentInstance {\n  id: tokenId\n  tokenId\n  owner\n  equipmentId\n  alias\n  equipmentType\n  slot\n  name\n  rarity\n  collections\n  equippedBy\n  __typename\n}\n"
        }
        try:
            r = requests.post(url=marketplace_endpoint,
                              json=query,
                              headers={'content-type': 'application/json'})
            if r.status_code != 200:
                logging.info('Status code: {r.status_code}')
                return None
            else:
                return json.loads(r.text)['data']['axie']['newGenes']
        except requests.exceptions.RequestException as error:
                logging.info(f"Axie id: {self.axie_id}. Gen can't be accessed due to: {error}.")

    def retrieve_parts_from_genes(self):
        """ Retrieves information from gene string.

            :return: str - 'class', dict - axie part_ids
        """

        try:
            gene = AxieGene(hex_string=self.axie_genes, hex_type=512)
        except KeyError:
            logging.info(f'id({self.axie_id}): genes KeyError')
            return None, None
        return gene.genes['cls'].capitalize(), {part: gene.genes[part]['d']['partId'] for part in parts}

    def get_twins(self, size: int = 2):
        """Get twin axies

            :param size: number of marketplace twins return.
            :return: pandas Dataframe with twin axies {id, price, link}
            """

        query = {
            "operationName": "GetAxieBriefList",
            "variables": {
                "from": 0,
                "size": size,
                "sort": "PriceAsc",
                "auctionType": "Sale",
                "criteria": {
                    'parts': list(self.axie_parts.values()),
                    'classes': self.axie_class
                }
            },
            "query": "query GetAxieBriefList($auctionType: AuctionType, $criteria: AxieSearchCriteria, $from: Int, $sort: SortBy, $size: Int, $owner: String) {\n  axies(\n    auctionType: $auctionType\n    criteria: $criteria\n    from: $from\n    sort: $sort\n    size: $size\n    owner: $owner\n  ) {\n    total\n    results {\n      ...AxieBrief\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment AxieBrief on Axie {\n  id\n  name\n  stage\n  class\n  breedCount\n  image\n  title\n  genes\n  newGenes\n  battleInfo {\n    banned\n    __typename\n  }\n  order {\n    id\n    currentPrice\n    currentPriceUsd\n    __typename\n  }\n  parts {\n    id\n    name\n    class\n    type\n    specialGenes\n    __typename\n  }\n  __typename\n}\n"
        }
        try:
            r = requests.post(url=marketplace_endpoint,
                              json=query,
                              headers={'content-type': 'application/json'})
            if r.status_code != 200:
                logging.info(f'get_similar_axies status_code: {r.status_code}')
                return None
            similar_axies_raw = json.loads(r.text)['data']['axies']
            if similar_axies_raw['total'] == 0:
                logging.debug(f"No twin axies acessible on marketplace for id: {self.axie_id}")
                return None
        except requests.exceptions.RequestException as error:
            logging.info(f"Axie id: {self.axie_id} Twins can't be accessed due to: {error}.")

        self.twins = [{'id': axie['id'], 'price': axie['order']['currentPriceUsd']}
                      for axie in similar_axies_raw['results']]
        if size == 1:
            return self.twins[0]

    def update(self):
        self.__init__(axie_id=self.axie_id)  # Should be reworked.


class AxieReturnHandler():

    def __init__(self, axie_user: AxieUser = None, axie: Axie = None):
        self.axie_user = axie_user
        self.axie = axie
        pass

def cprofile_test():
    profile = cProfile.Profile()
    profile.runcall(AxieUser.get_leaderboard_team_prices,
                    number_of_places=20,
                    offset=1000,
                    log_output=True)
    ps = pstats.Stats(profile)
    ps.sort_stats("cumtime").print_stats("main_rework.py")




# ax = Axie(1601978)
# ax.update()
# ids = [1639675, 3846958, 7299965]
# us = AxieUser(sample_user_id)
cprofile_test()
# out = AxieUser.get_leaderboard_team_prices(log_output=True)
# a = 6

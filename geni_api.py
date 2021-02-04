import time
import requests
from collections import defaultdict
from enum import Enum

GENI_BASE_URL = 'https://www.geni.com/api/'

UnionRel = Enum('UnionRel', 'partner child')
HumanRel = Enum('HumanRel', 'parent sibling child partner self')


def _filter_node_types(nodes, node_type: str):
    return {k: v for k, v in nodes.items() if k.startswith(node_type)}


def _rel(union) -> UnionRel:
    return UnionRel[union['rel']]


def _compute_rel_to_self(self_in_union: UnionRel,
                                  other_in_union: UnionRel) -> HumanRel:
    if self_in_union == UnionRel.partner and other_in_union == UnionRel.partner:
        return HumanRel.partner
    if self_in_union == UnionRel.child and other_in_union == UnionRel.child:
        return HumanRel.sibling
    if self_in_union == UnionRel.partner and other_in_union == UnionRel.child:
        return HumanRel.child
    if self_in_union == UnionRel.child and other_in_union == UnionRel.partner:
        return HumanRel.parent


class GeniApi:
    def __init__(self):
        with open('access-token', 'r') as f:
            args = {}
            for line in f:
                k, v = line.strip().split(',')
                args[k] = v
            response = requests.get('https://www.geni.com/platform/oauth/request_token', args)
            j = response.json()
            self.access_token = j['access_token']
            print(self.access_token)

    def _request(self, method, api, args):
        time.sleep(.25)  # rate limit to 40/10s
        args['access_token'] = self.access_token
        url = f'{GENI_BASE_URL}{api}'
        response = method(url, args)
        for i in range(1, 4):
            if response.status_code == 200:
                break
            if response.status_code == 429:
                time.sleep(i)
            response = method(url, args)
        response.raise_for_status()
        return response.json()

    def get(self, api, args=None):
        args = args or {}
        return self._request(requests.get, api, args)

    def post(self, api, args):
        return self._request(requests.post, api, args)

    def get_profile(self, profile_id='profile', fields=None):
        args = {}
        if fields:
            args['fields'] = ','.join(fields)
        return self.get(profile_id, args)

    def update_profile(self, profile_id, fields):
        self.post(f'{profile_id}/update-basics', fields)

    def get_immediate_family(self, base_profile_id):
        j = self.get(f'{base_profile_id}/immediate-family')

        # Update profile id for cases where the guid was used.
        base_profile_id = j['focus']['id']

        nodes = j['nodes']
        profiles = _filter_node_types(nodes, 'profile')

        # For each profile, figure out rel
        union_rels = {union_id: _rel(union) for union_id, union in profiles[base_profile_id]['edges'].items()}

        rels = []
        family = defaultdict(list)

        for profile_id, profile in profiles.items():
            if profile_id == base_profile_id:
                family[HumanRel.self] = [profile]
                continue
            for union_id, union in profile['edges'].items():
                if union_id not in union_rels.keys():
                    continue
                rel_to_self = _compute_rel_to_self(union_rels[union_id], _rel(union))
                rels.append((profile, rel_to_self))

        for rel in rels:
            family[rel[1]].append(rel[0])

        return family


if __name__ == '__main__':
    my_family = GeniApi().get_immediate_family('profile-11318249')
    for rel, people in my_family.items():
        print(rel)
        for person in people:
            print(person['first_name'], person['last_name'])
        print()


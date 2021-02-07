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


def _read_csv(file_path: str):
    data = {}
    with open(file_path, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            k, v = line.strip().split(',')
            data[k] = v
    return data


class GeniApi:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        now = int(time.time())
        args = _read_csv('client-info')
        access_info = _read_csv('access-token')
        if 'access_token' in access_info and 'expiry' in access_info and now < int(access_info['expiry']):
            self.access_token = args['access_token']
            return
        if 'refresh_token' in access_info:
            args['refresh_token'] = access_info['refresh_token']
            args['grant_type'] = 'refresh_token'
        response = requests.get('https://www.geni.com/platform/oauth/request_token', args)
        j = response.json()
        self.access_token = j['access_token']
        j['expiry'] = now + j['expires_in']
        with open('access-token', 'w') as f:
            f.writelines([f'{k},{v}\n' for k, v in j.items()])

    def _request(self, method, api, args):
        if self.dry_run:
            print(method, api, args)
            return {}
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
        if response.status_code != 200:
            print(method, url, args, response.json())
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

    def get_partner_unions(self, profile_id):
        j = self.get(f'{profile_id}/immediate-family')

        # Update profile id for cases where the guid was used.
        base_profile_id = j['focus']['id']

        profile = j['nodes'][base_profile_id]

        return [union_id for union_id, union in profile['edges'].items() if union['rel'] == 'partner']

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

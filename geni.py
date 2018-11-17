import json
import time
import urllib.request
import urllib.parse
import urllib.error
from queue import Queue
from anytree import Node

from family_tree import FamilyTree, Person, PersonData

GENI_BASE_URL = 'https://www.geni.com/api/'


def geni_to_person_data(geni_data):
    first, last = geni_data.get('first_name', ''), geni_data.get('last_name', '')
    return PersonData(id=geni_data['id'], first_name=first, last_name=last,
                      display_name=geni_data.get('display_name', '{} {}'.format(first, last)))


def get_name(profile):
    if 'display_name' in profile:
        return profile['display_name']
    return '{} {}'.format(profile.get('first_name', ''), profile.get('last_name', ''))


class GeniFamilyTreeGenerator:
    def __init__(self):
        with open('access-token', 'r') as f:
            self.access_token = f.read()
        self.base_profile = self.geni_get('profile', {})

    def geni_get(self, api, args):
        args['access_token'] = self.access_token
        url = '{}{}?{}'.format(GENI_BASE_URL, api, urllib.parse.urlencode(args))
        response = urllib.request.urlopen(url)
        return json.loads(response.read())

    def get_immediate_family(self, profile_id):
        j = self.geni_get('{}/{}'.format(profile_id, 'immediate-family'), {})
        unions = filter(lambda x: x.startswith('union'), j['nodes'].keys())
        parents = []
        children = []

        filter_position = lambda edges, position: map(lambda x: j['nodes'][x],
                                                      filter(lambda k: union_edges[k]['rel'] == position, edges))

        for union in unions:
            union_details = j['nodes'][union]
            union_edges = union_details['edges']
            profile_position = union_edges[profile_id]['rel']
            if profile_position == 'child':
                assert len(parents) == 0
                parents = filter_position(edges=union_edges, position='partner')
            elif profile_position == 'partner':
                children += filter_position(edges=union_edges, position='child')
        return parents, children

    def enqueue_all(self, queue, items_to_enqueue, parent, processed):
        for tree_child in items_to_enqueue:
            if tree_child['id'] not in processed:
                queue.put(
                    Node(name=tree_child['id'], parent=parent, data=geni_to_person_data(tree_child)))
            else:
                print(tree_child['id'], 'already processed!')

    def process_queue(self, queue, max_depth, processing_ancestors):
        processed = {}
        new_queue = Queue()
        new_queue_keys = set()
        while not queue.empty():
            current_node = queue.get()
            current_id = current_node.name
            processed[current_id] = current_node
            if current_node.depth >= max_depth:
                continue
            print('Processing', current_id, current_node.data.display_name, '...')
            try:
                parents, children = self.get_immediate_family(current_id)
                self.enqueue_all(queue, parents if processing_ancestors else children, current_node, processed)
                if processing_ancestors:
                    self.enqueue_all(new_queue, children, current_node, new_queue_keys)
                    new_queue_keys = new_queue_keys.union([child['id'] for child in children])
            except urllib.error.HTTPError as e:
                print('Error!', e, current_node)
            time.sleep(.25)  # rate limit to 40/10s
        return processed, new_queue

    def generate_tree(self, max_depth=10):
        """:rtype FamilyTree"""
        root_profile = self.base_profile
        root = Node(name=root_profile['id'], data=geni_to_person_data(root_profile))
        ancestors_q = Queue()
        ancestors_q.put(root)
        processed_ancestors, descendants_q = self.process_queue(ancestors_q, max_depth, processing_ancestors=True)
        # processed_descendants, _ = self.process_queue(descendants_q, max_depth, processing_ancestors=False)
        processed_descendants = {}
        processed = {}
        for k, v in processed_ancestors.items():
            processed[k] = Person(data=v.data, ancestors=v, descendants=processed_descendants[k] if k in processed_descendants else None)
        for k, v in processed_descendants.items():
            if k not in processed:
                processed[k] = Person(data=v.data, ancestors=None, descendants=v)
        return FamilyTree(root=root_profile['id'], people=processed)




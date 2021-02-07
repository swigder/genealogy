from collections import namedtuple
from functools import partial
from typing import Optional

from geni_api import GeniApi
from update_lib import update_items, Update, Updater

ProfileAdd = namedtuple('ProfileAdd', ['profile_id', 'profile', 'method'])


class Commands:
    END_NEW = 'end_new'
    POP_ROOTS = 'pop_roots'
    POP_ROOT = 'pop_root'
    PUSH_ROOT = 'push_root'
    SET_ROOT = 'set_root'
    UPDATE_PROFILE = 'update_profile'
    ADD_CHILDREN = 'add_children'
    ADD_PARTNER = 'add_partner'
    ADD_PARENTS = 'add_parents'
    ADD_TREE = 'add_tree'


COMMANDS = Commands.__dict__.values()


GENI_APIS = {
    Commands.ADD_TREE: 'add',
    Commands.ADD_PARENTS: 'add-parent',
    Commands.ADD_PARTNER: 'add-partner',
    Commands.ADD_CHILDREN: 'add-child',
    Commands.UPDATE_PROFILE: 'update',
}

MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

KNOWN_CITIES = {
    'Balkany': {'city': 'Balkány', 'state': 'Szabolcs-Szatmár-Bereg', 'country': 'Hungary'},
    'Dej': {'city': 'Dej', 'state': 'Cluj', 'country': 'Romania'},
    'Mezö-Csáth': {'city': 'Mezőcsát', 'state': 'Borsod-Abaúj-Zemplén', 'country': 'Hungary'},
    'Nagyvarad': {'city': 'Oradea', 'state': 'Bihor', 'country': 'Romania'},
    'Szeged': {'city': 'Szeged', 'state': 'Csongrád', 'country': 'Hungary'},
}

DEFAULTS = {
    'living': False,
}

DICTS = {
    'gender': {
        'f': 'female',
        'm': 'male',
        'o': 'unknown',
    }
}


def key_from_file(key, file_info):
    if key in file_info:
        return {key: file_info[key]}
    return {}


def key_with_default(key, file_info):
    if key in file_info:
        return {key: file_info[key]}
    return {key: DEFAULTS[key]}


def key_from_dict(key, file_info):
    if key in file_info:
        nonstandard_value = file_info[key]
        return {key: DICTS[key][nonstandard_value]}


def age_extractor(file_info):
    if 'age' in file_info:
        age, year = file_info['age'].strip().split(':', maxsplit=1)
        age_years = int(year) - int(age)
        return {'birth[date][year]': age_years}


def name_extractor(file_info):
    if 'name' in file_info:
        return {'last_name': (file_info['name'].split(', ', maxsplit=1))[0],
                'first_name': (file_info['name'].split(', ', maxsplit=1))[1]}


def event_extractor(event, file_info):
    geni_data = {}

    if f'{event}_date' in file_info:
        day, month, year = file_info[f'{event}_date'].split('-')
        geni_data[f'{event}[date][year]'] = int(year)
        geni_data[f'{event}[date][month]'] = MONTHS.index(month.lower()[:3]) + 1
        geni_data[f'{event}[date][day]'] = int(day)

    if f'{event}_town' in file_info:
        event_town = file_info[f'{event}_town']
        if event_town in KNOWN_CITIES:
            for key, value in KNOWN_CITIES[event_town].items():
                geni_data[f'{event}[location][{key}]'] = value
        else:
            geni_data[f'{event}[location][city]'] = event_town

    return geni_data


def extractors_for_keys(keys, extractor):
    return [(key, partial(extractor, key)) for key in keys]


DATA_EXTRACTORS = [('age', age_extractor), ('name', name_extractor)] \
                  + extractors_for_keys(['about_me', 'last_name', 'maiden_name', 'first_name', 'nicknames'],
                                        key_from_file) \
                  + extractors_for_keys(['birth', 'death', 'marriage'], event_extractor) \
                  + extractors_for_keys(DEFAULTS.keys(), key_with_default) \
                  + extractors_for_keys(DICTS.keys(), key_from_dict)

KEYS_CAPITALIZE = ['last_name', 'first_name', 'maiden_name']

DATA_UPDATERS = {
    lambda _, v: v.strip() if isinstance(v, str) else v,
    lambda k, v: v.title() if k in KEYS_CAPITALIZE else v,
}


class ProfileAdder(Updater):
    def __init__(self, geni_api: GeniApi, command, base_profile, union_id=None):
        self.geni_api = geni_api
        self.command = command
        self.base_profile = base_profile
        self.union_id = union_id

    def get_update(self, file_profile) -> Optional[Update]:
        profile = {}

        for key, extractor in DATA_EXTRACTORS:
            profile.update(extractor(file_profile) or {})

        for updater in DATA_UPDATERS:
            for key, value in profile.items():
                profile[key] = updater(key, value)

        # merge with base logic
        if self.command == Commands.UPDATE_PROFILE:
            if 'nicknames' in profile and 'nicknames' in self.base_profile:
                profile['nicknames'] = ','.join(profile['nicknames'].split(',') + self.base_profile['nicknames'])
            if 'about_me' in profile and 'about_me' in self.base_profile:
                profile['about_me'] = self.base_profile['about_me'] + '\r\n' + '-' * 10 + '\r\n' + profile['about_me']
        else:
            for key in ['about_me', 'last_name']:
                if key in self.base_profile and key not in profile:
                    profile[key] = self.base_profile[key]
            if self.command == Commands.ADD_PARENTS and 'maiden_name' in self.base_profile:
                profile['last_name'] = self.base_profile['maiden_name']

        profile_to_add_to = self.union_id if self.union_id and self.command == Commands.ADD_CHILDREN else self.base_profile[
            'id']
        method = GENI_APIS[self.command]

        return Update(f'{profile_to_add_to}/{method}: {profile}',
                      ProfileAdd(profile_id=profile_to_add_to, profile=profile, method=method))

    def do_update(self, update: ProfileAdd):
        # https://www.geni.com/api/profile-122248213/add-parent?first_name=Mike&names[de][first_name]=Mike
        return self.geni_api.post(f'{update.profile_id}/{update.method}', update.profile)


class FileProcessor:
    def __init__(self):
        self.geni_api = GeniApi(dry_run=False)
        self.current_command = None
        self.current_base_profile = None
        self.current_union_id = None
        self.base_profile_stack = []
        self.all_profiles_added = []

    def process_file(self, filename):
        current_info = {}
        current_infos = []

        with open(filename, 'r') as f:
            line_number = 0
            for line in f:
                line_number += 1
                line = line.strip()
                if line and line not in COMMANDS and ': ' not in line:
                    raise Exception(f'Bad line {line_number}: {line}')
                if line == Commands.END_NEW:
                    break

        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()

                if line in COMMANDS:
                    if line == Commands.END_NEW:
                        break
                    if self.current_command:
                        self.run_current_command(current_infos)
                        current_infos = []
                    self.current_command = line
                elif not line and current_info:
                    current_infos.append(current_info)
                    current_info = {}
                else:
                    elements = line.split(':', maxsplit=1)
                    if len(elements) == 2:
                        current_info[elements[0]] = elements[1].strip()

            if current_info:
                current_infos.append(current_info)
            if current_infos:
                self.run_current_command(current_infos)

        # run command

    def set_root(self, info):
        self.set_base_profile(None)
        if 'id' in info:
            profile_id = 'profile-g' + info['id']
            self.set_base_profile(self.geni_api.get_profile(profile_id,
                                                            fields=['id', 'about_me', 'last_name', 'maiden_name',
                                                                    'nicknames', 'name']))
        else:
            for profile_keys, profile in self.all_profiles_added:
                all_keys_match = True
                for key, value in info.items():
                    if key not in profile_keys or profile_keys[key] != value:
                        all_keys_match = False
                        break
                if all_keys_match:
                    self.set_base_profile(profile)

    def set_base_profile(self, profile):
        self.current_base_profile = profile
        self.current_union_id = None
        if profile and 'name' in profile:
            print(f'Base profile has been updated to {self.current_base_profile["name"]}')
        else:
            print('Base profile has been reset')

    def update_root_stack(self):
        if self.current_command == Commands.PUSH_ROOT:
            self.base_profile_stack.append(self.current_base_profile)
            self.set_base_profile(self.all_profiles_added[-1])
        elif self.current_command == Commands.POP_ROOT:
            self.set_base_profile(self.base_profile_stack.pop())
        elif self.current_command == Commands.POP_ROOTS:
            self.set_base_profile(self.base_profile_stack[0])
            self.base_profile_stack.clear()

    def add_profiles(self, profiles_to_add):
        profile_adder = ProfileAdder(self.geni_api, command=self.current_command,
                                     base_profile=self.current_base_profile, union_id=self.current_union_id)
        profiles_added = update_items(profile_adder, profiles_to_add)
        self.all_profiles_added.extend(zip(profiles_to_add, profiles_added))
        return profiles_added

    def run_current_command(self, infos):
        if self.current_command == Commands.SET_ROOT:
            assert len(infos) == 1
            self.set_root(infos[0])
        elif self.current_command in [Commands.PUSH_ROOT, Commands.POP_ROOT, Commands.POP_ROOTS]:
            assert len(infos) == 0
            self.update_root_stack()
        else:
            if self.current_command == Commands.ADD_TREE:
                self.set_base_profile({'id': 'profile'})
                self.base_profile_stack = []
            elif self.current_command == Commands.ADD_CHILDREN and not self.current_union_id:
                unions = self.geni_api.get_partner_unions(self.current_base_profile['id'])
                self.current_union_id = unions[0] if len(unions) == 1 else None
            just_added = self.add_profiles(profiles_to_add=infos)
            if self.current_command == Commands.ADD_TREE:
                self.set_base_profile(just_added[0])


if __name__ == '__main__':
    FileProcessor().process_file(filename='profile.txt')

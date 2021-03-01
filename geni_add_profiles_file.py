from collections import namedtuple
from functools import partial
from typing import Optional

import unidecode as unidecode

from geni_api import GeniApi
from known_cities import KNOWN_CITIES
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
    ADD_MARRIAGE = 'add_marriage'


COMMANDS = Commands.__dict__.values()

GENI_APIS = {
    Commands.ADD_TREE: 'add',
    Commands.ADD_PARENTS: 'add-parent',
    Commands.ADD_PARTNER: 'add-partner',
    Commands.ADD_CHILDREN: 'add-child',
    Commands.UPDATE_PROFILE: 'update',
}

MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

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

BASE_PROFILE_FIELDS = ['id', 'about_me', 'last_name', 'maiden_name', 'nicknames', 'name']


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


def name_extractor(key, split_keys, file_info):
    if key in file_info:
        unsplit = file_info[key]
        if ',' in unsplit:
            split = unsplit.split(',', maxsplit=len(split_keys) - 1)
        elif '(' in unsplit and unsplit.endswith(')'):
            split = reversed(unsplit.strip()[:-1].split('(', maxsplit=len(split_keys) - 1))
        else:
            split = unsplit
        return {k: v.strip() for k, v in zip(split_keys, split)}


def event_extractor(event, file_info):
    geni_data = {}

    if f'{event}_date' in file_info:
        day, month, year = file_info[f'{event}_date'].split('-')
        geni_data[f'{event}[date][year]'] = int(year)
        geni_data[f'{event}[date][month]'] = MONTHS.index(month.lower()[:3]) + 1
        geni_data[f'{event}[date][day]'] = int(day)

    if f'{event}_town' in file_info:
        event_town = file_info[f'{event}_town']
        event_town_decoded = unidecode.unidecode(event_town)
        if event_town_decoded in KNOWN_CITIES:
            for key, value in KNOWN_CITIES[event_town_decoded].items():
                geni_data[f'{event}[location][{key}]'] = value
        else:
            geni_data[f'{event}[location][city]'] = event_town

    return geni_data


def extractors_for_keys(keys, extractor):
    if isinstance(keys, dict):
        return [(key, partial(extractor, key, args)) for key, args in keys.items()]
    return [(key, partial(extractor, key)) for key in keys]


DATA_EXTRACTORS = [('age', age_extractor)] \
                  + extractors_for_keys({'name': ['last_name', 'first_name'],
                                         'birth_name': ['maiden_name', 'first_name']}, name_extractor) \
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

        profile_to_add_to = self.union_id if self.union_id and self.command == Commands.ADD_CHILDREN else \
            self.base_profile['id']
        method = GENI_APIS[self.command]

        return Update(f'{profile_to_add_to}/{method}: {profile}',
                      ProfileAdd(profile_id=profile_to_add_to, profile=profile, method=method))

    def do_update(self, update: ProfileAdd):
        # https://www.geni.com/api/profile-122248213/add-parent?first_name=Mike&names[de][first_name]=Mike
        return self.geni_api.post(f'{update.profile_id}/{update.method}', update.profile)


class FileProcessor:
    def __init__(self):
        self.geni_api = GeniApi(dry_run=False)
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

                if line.startswith('#'):
                    continue

                if line and line not in COMMANDS and ': ' not in line:
                    raise Exception(f'Bad line {line_number}: {line}')
                if line == Commands.END_NEW:
                    break

        current_command = None
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()

                if line in COMMANDS:
                    if line == Commands.END_NEW:
                        break
                    if current_command:
                        self.run_command(current_command, current_infos)
                        current_infos = []
                    current_command = line
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
                self.run_command(current_command, current_infos)

        # run command

    def set_root(self, info):
        self.set_base_profile(None)
        if 'id' in info:
            profile_id = 'profile-g' + info['id']
            self.set_base_profile(self.geni_api.get_profile(profile_id, fields=BASE_PROFILE_FIELDS))
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
        if profile and 'id' in profile and 'about_me' not in profile:
            existing_profile = self.geni_api.get_profile('profile-' + profile['id'], fields=BASE_PROFILE_FIELDS)
            if 'results' not in existing_profile:
                profile = existing_profile
        self.current_base_profile = profile
        self.current_union_id = None
        if profile and 'name' in profile:
            print(f'Base profile has been updated to {self.current_base_profile["name"]}')
        else:
            print('Base profile has been reset')

    def update_root_stack(self, command):
        if command == Commands.PUSH_ROOT:
            self.base_profile_stack.append(self.current_base_profile)
            self.set_base_profile(self.all_profiles_added[-1][1])
        elif command == Commands.POP_ROOT:
            self.set_base_profile(self.base_profile_stack.pop())
        elif command == Commands.POP_ROOTS:
            self.set_base_profile(self.base_profile_stack[0])
            self.base_profile_stack.clear()

    def add_profiles(self, command, profiles_to_add):
        profile_adder = ProfileAdder(self.geni_api, command=command,
                                     base_profile=self.current_base_profile, union_id=self.current_union_id)
        profiles_added = update_items(profile_adder, profiles_to_add)
        self.all_profiles_added.extend(zip(profiles_to_add, profiles_added))
        return profiles_added

    @staticmethod
    def convert_marriage_to_profile_commands(infos):
        info_map = {info['section']: info for info in infos}

        marriage_info = info_map['marriage']
        marriage_year = marriage_info['date'].split('-')[-1]

        commands = []

        groom_info = {k: v for k, v in info_map['groom'].items() if k not in ['parents']}
        groom_info['about_me'] = marriage_info['record']
        groom_info['age'] = f'{groom_info["age"]}:{marriage_year}'
        groom_info['gender'] = 'm'
        commands.append((Commands.ADD_TREE, groom_info))

        groom_parents = info_map['groom']['parents'].split('/')
        commands.append((Commands.ADD_PARENTS, {'first_name': groom_parents[0], 'gender': 'm'}))
        commands.append((Commands.ADD_PARENTS, {'birth_name': groom_parents[1], 'gender': 'f'}))

        bride_info = {k: v for k, v in info_map['bride'].items() if k not in ['parents']}
        bride_info['age'] = f'{bride_info["age"]}:{marriage_year}'
        bride_info['gender'] = 'f'
        bride_info['birth_name'] = bride_info['name']
        del bride_info['name']
        bride_info['marriage_date'] = marriage_info['date']
        bride_info['marriage_town'] = marriage_info['town']
        commands.append((Commands.ADD_PARTNER, bride_info))

        commands.append((Commands.PUSH_ROOT, {}))
        bride_parents = info_map['bride']['parents'].split('/')
        commands.append((Commands.ADD_PARENTS, {'first_name': bride_parents[0], 'gender': 'm'}))
        commands.append((Commands.ADD_PARENTS, {'birth_name': bride_parents[1], 'gender': 'f'}))

        return commands

    def run_command(self, command, infos):
        if command == Commands.SET_ROOT:
            assert len(infos) == 1
            self.set_root(infos[0])
        elif command in [Commands.PUSH_ROOT, Commands.POP_ROOT, Commands.POP_ROOTS]:
            assert len(infos) == 0 or (len(infos) == 1 and not infos[0])
            self.update_root_stack(command)
        elif command in [Commands.ADD_MARRIAGE]:
            commands = self.convert_marriage_to_profile_commands(infos)
            for command, info in commands:
                self.run_command(command, [info])
        else:
            if command == Commands.ADD_TREE:
                self.set_base_profile({'id': 'profile'})
                self.base_profile_stack = []
            elif command == Commands.ADD_CHILDREN and not self.current_union_id:
                unions = self.geni_api.get_partner_unions(self.current_base_profile['id'])
                self.current_union_id = unions[0] if len(unions) == 1 else None
            just_added = self.add_profiles(command, profiles_to_add=infos)
            if command == Commands.ADD_TREE:
                self.set_base_profile(just_added[0])


if __name__ == '__main__':
    FileProcessor().process_file(filename='profile.geni')

from collections import namedtuple
from functools import partial
from typing import Optional

from geni_api import GeniApi
from update_lib import update_items, Update, Updater

ProfileAdd = namedtuple('ProfileAdd', ['profile_id', 'profile', 'method'])

COMMANDS = {
    'add_tree': 'add',
    'add_parents': 'add-parent',
    'add_partner': 'add-partner',
    'add_children': 'add-child',
    'set_root': None,
}

MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

KNOWN_CITIES = {
    'Balkany': {'city': 'Balk\u00e1ny', 'country': 'Hungary', 'postal_code': '4233',
                'latitude': 47.7666746, 'longitude': 21.8400133},
    'Nagyvarad': {'city': 'Oradea', 'county': 'Municipiul Oradea', 'state': 'BH', 'country': 'Romania',
                  'postal_code': '410100', 'latitude': 47.0515885, 'longitude': 21.9428476, },
    'Dej': {'city': 'Dej', 'county': 'Dej', 'state': 'CJ', 'country': 'Romania',
            'postal_code': '405200', 'latitude': 47.1415878, 'longitude': 23.8787342, },
}

DEFAULTS = {
    'is_alive': False,
    'living': False,
}

DICTS = {
    'gender': {
        'f': 'female',
        'm': 'male',
        'o': 'unknown',
    }
}


def key_from_file(key, file_info, _):
    if key in file_info:
        return {key: file_info[key]}
    return {}


def key_from_file_base_profile_fallback(key, file_info, base_profile):
    if key in file_info:
        return {key: file_info[key]}
    if key in base_profile:
        return {key: base_profile[key]}
    return {}


def key_with_default(key, file_info, _):
    if key in file_info:
        return {key: file_info[key]}
    return {key: DEFAULTS[key]}


def key_from_dict(key, file_info, _):
    if key in file_info:
        return {key: DICTS[key][[file_info][key]]}
    return {}


def age_extractor(file_info, _):
    if 'age' in file_info:
        age, year = file_info['age'].strip().split(':', maxsplit=1)
        age_years = int(year) - int(age)
        return {'birth[date][year]': age_years}


def name_extractor(file_info, _):
    return {'last_name': (file_info['name'].split(', ', maxsplit=1))[0],
            'first_name': (file_info['name'].split(', ', maxsplit=1))[1]}


def event_extractor(event, file_info, _):
    geni_data = {}

    if f'{event}_date' in file_info:
        day, month, year = file_info[f'{event}_date'].split('-')
        geni_data[f'{event}[date][year]'] = int(year)
        geni_data[f'{event}[date][month]'] = MONTHS.index(month.lower()[:3])
        geni_data[f'{event}[date][day]'] = int(day)

    if f'{event}_town' in file_info:
        event_town = file_info[f'{event}_town']
        if event_town in KNOWN_CITIES:
            for key, value in KNOWN_CITIES[event_town].items():
                geni_data[f'{event}[location][{key}]'] = value

    return geni_data


def extractors_for_keys(keys, extractor):
    return [(key, partial(extractor(key))) for key in keys]


KEYS_DEFAULT_FROM_BASE = ['last_name', 'about_me']

DATA_EXTRACTORS = [('age', age_extractor)] \
                  + extractors_for_keys(KEYS_DEFAULT_FROM_BASE, key_from_file_base_profile_fallback) \
                  + [('name', name_extractor)] \
                  + extractors_for_keys(['maiden_name', 'first_name'], key_from_file) \
                  + extractors_for_keys(['birth', 'death'], event_extractor) \
                  + extractors_for_keys(DEFAULTS.keys(), key_with_default) \
                  + extractors_for_keys(DICTS.keys(), key_from_dict)

KEYS_CAPITALIZE = ['last_name', 'first_name', 'maiden_name']

DATA_UPDATERS = {
    lambda _, v: v.strip() if isinstance(v, str) else v,
    lambda k, v: v.capitalize() if k in KEYS_CAPITALIZE else v,
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
            profile = profile | extractor(file_profile, self.base_profile)

        for key, value in profile.items():
            for updater in DATA_UPDATERS:
                profile[key] = updater(key, value)

        profile_to_add_to = self.union_id if self.union_id and self.command == 'add_children' else self.base_profile[
            'id']
        method = COMMANDS[self.command]

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
        self.all_profiles_added = []

    def process_file(self, filename):
        current_info = {}
        current_infos = []

        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line in COMMANDS:
                    if current_infos:
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
        self.current_base_profile = None
        self.current_union_id = None
        if 'id' in info:
            profile_id = 'profile-g' + info['id']
            self.current_base_profile = self.geni_api.get_profile(profile_id, fields=KEYS_DEFAULT_TO_BASE + ['id'])
        else:
            for profile_keys, profile in self.all_profiles_added:
                all_keys_match = True
                for key, value in info.items():
                    if key not in profile_keys or profile_keys[key] != value:
                        all_keys_match = False
                        break
                if all_keys_match:
                    self.current_base_profile = profile

    def add_profiles(self, profiles_to_add):
        profile_adder = ProfileAdder(self.geni_api, command=self.current_command,
                                     base_profile=self.current_base_profile, union_id=self.current_union_id)
        profiles_added = update_items(profile_adder, profiles_to_add)
        self.all_profiles_added.extend(zip(profiles_to_add, profiles_added))
        return profiles_added

    def run_current_command(self, infos):
        if self.current_command == 'set_root':
            assert len(infos) == 1
            self.set_root(infos[0])
        else:
            if self.current_command == 'add_tree':
                self.current_base_profile = {'id': 'profile'}
            elif self.current_command == 'add_children' and not self.current_union_id:
                unions = self.geni_api.get_partner_unions(self.current_base_profile['id'])
                self.current_union_id = unions[0] if len(unions) == 1 else None
            just_added = self.add_profiles(profiles_to_add=infos)
            if self.current_command == 'add_tree':
                self.current_base_profile = just_added[0]


if __name__ == '__main__':
    FileProcessor().process_file(filename='profile.txt')

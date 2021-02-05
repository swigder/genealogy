from collections import namedtuple
from functools import partial
from typing import Optional

from geni_api import GeniApi
from update_lib import update_items, Update, Updater

ProfileAdd = namedtuple('ProfileAdd', ['profile_id', 'profile'])


GENDERS = {
    'f': 'female',
    'm': 'male',
    'o': 'unknown',
}


class ParentUpdater(Updater):
    def __init__(self, geni_api: GeniApi, profile_id: str, about_me: str):
        self.geni_api = geni_api
        self.profile_id = profile_id
        self.about_me = about_me

    def get_update(self, _: str) -> Optional[Update]:
        name = input("Name? Last, first or first.")
        names = name.split(', ')
        if len(names) == 1:
            first_name = names[0]
            last_name = input("Last name?")
        elif len(names) == 2:
            first_name = names[1]
            last_name = names[0]
        else:
            raise
        first_name = first_name.capitalize()
        last_name = last_name.capitalize()
        maiden_name = input("Birth name?").capitalize()
        gender = GENDERS[input("Gender? f/m/o")]
        profile = {
            'first_name': first_name,
            'last_name': last_name,
            'maiden_name': maiden_name,
            'gender': gender,
            'about_me': self.about_me,
        }
        return Update(f'{profile}', ProfileAdd(profile_id=self.profile_id, profile=profile))

    def do_update(self, update: ProfileAdd):
        # https://www.geni.com/api/profile-122248213/add-parent?first_name=Mike&names[de][first_name]=Mike
        self.geni_api.post(f'{update.profile_id}/add-parent', update.profile)


if __name__ == '__main__':
    geni_api = GeniApi()
    profile_id = 'profile-g' + input('Profile id?')
    profile = geni_api.get_profile(profile_id, ['name', 'about_me'])
    print(f"{profile['name']}:")
    if 'about_me' in profile:
        print(f"{profile['about_me']}")
        about_me = profile['about_me']
    else:
        about_me = input("About me?")

    to_add = int(input('How many parents?'))

    update_items(ParentUpdater(geni_api, profile_id, about_me), range(1, to_add + 1))

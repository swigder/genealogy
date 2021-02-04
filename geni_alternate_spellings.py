from collections import namedtuple
from typing import Set, List, Optional

from geni_api import GeniApi

Update = namedtuple('Update', ['message', 'update'])
NicknameUpdate = namedtuple('NicknameUpdate', ['profile_id', 'nicknames'])


def get_alternate_spellings(geni_api: GeniApi, profile_id: str, spellings: Set[str]) -> Optional[Update]:
    profile = geni_api.get_profile(profile_id, fields=['name', 'first_name', 'maiden_name', 'last_name', 'nicknames'])
    nicknames = profile['nicknames'] if 'nicknames' in profile else []
    existing_spellings = set(nicknames)
    for key in {'first_name', 'last_name', 'maiden_name'}:
        if key in profile:
            existing_spellings.add(profile[key])
    leftover_spellings = spellings.difference(existing_spellings)
    if not leftover_spellings:
        return None
    nicknames.extend(leftover_spellings)
    return Update(message=f"{profile_id} {profile['name']} ({existing_spellings}): {nicknames}",
                  update=(NicknameUpdate(profile_id, nicknames)))


def add_alterate_spellings(geni_api: GeniApi, updates: List[Update]):
    for update in updates:
        geni_api.update_profile(update.update.profile_id, {'nicknames': ','.join(update.update.nicknames)})


def confirm_updates(updates: List[Update]) -> bool:
    for update in updates:
        print(update.message)
    return input("Confirm [y/N]").lower().strip() == 'y'


if __name__ == '__main__':
    geni_api = GeniApi()
    my_family = geni_api.get_immediate_family('profile-g6000000002032852609')
    family_members = [item for sublist in my_family.values() for item in sublist]
    spellings = {'Holczer', 'Holtzer'}
    updates = [get_alternate_spellings(geni_api, family_member['id'], spellings=spellings) for family_member in
               family_members]
    updates = list(filter(None, updates))
    if confirm_updates(updates):
        print(f'Continuing with {len(updates)} updates...')
        add_alterate_spellings(geni_api, updates)
        print('Done.')
    else:
        print('Cancelling...')

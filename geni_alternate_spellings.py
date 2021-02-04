from collections import namedtuple
from functools import partial
from typing import Set, List, Optional

from geni_api import GeniApi
from update_lib import update_items, Update

NicknameUpdate = namedtuple('NicknameUpdate', ['profile_id', 'nicknames'])


def get_alternate_spellings(geni_api: GeniApi, spellings: Set[str], profile_id: str) -> Optional[Update]:
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


if __name__ == '__main__':
    geni_api = GeniApi()
    my_family = geni_api.get_immediate_family('profile-g6000000002032852714')
    family_members = [item['id'] for sublist in my_family.values() for item in sublist]
    update_items(family_members, partial(get_alternate_spellings, geni_api, {'Holczer', 'Holtzer'}),
                 partial(add_alterate_spellings, geni_api))

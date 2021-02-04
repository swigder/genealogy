from typing import Set

from geni_api import GeniApi


def add_alterate_spelling(geni_api: GeniApi, profile_id, spellings: Set[str]):
    profile = geni_api.get_profile(profile_id, fields=['first_name', 'maiden_name', 'last_name', 'nicknames'])
    nicknames = profile['nicknames'] if 'nicknames' in profile else []
    existing_spellings = set(nicknames)
    for key in {'first_name', 'last_name', 'maiden_name'}:
        if key in profile:
            existing_spellings.add(profile[key])
    leftover_spellings = spellings.difference(existing_spellings)
    if not leftover_spellings:
        return
    nicknames.extend(leftover_spellings)
    print(profile, nicknames)
    geni_api.update_profile(profile_id, {'nicknames': ','.join(nicknames)})


if __name__ == '__main__':
    geni_api = GeniApi()
    my_family = geni_api.get_immediate_family('profile-g6000000002032852609')
    family_members = [item for sublist in my_family.values() for item in sublist]
    for family_member in family_members:
        add_alterate_spelling(geni_api, family_member['id'], spellings={'Holczer', 'Holtzer'})

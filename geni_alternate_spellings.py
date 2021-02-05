from collections import namedtuple
from typing import Set, Optional

from geni_api import GeniApi
from update_lib import update_items, Update, Updater

NicknameUpdate = namedtuple('NicknameUpdate', ['profile_id', 'nicknames'])


class SpellingUpdater(Updater):
    def __init__(self, geni_api: GeniApi, spellings: Set[str]):
        self.geni_api = geni_api
        self.spellings = spellings

    def get_update(self, profile_id: str) -> Optional[Update]:
        profile = self.geni_api.get_profile(profile_id, fields=['name', 'first_name', 'maiden_name', 'last_name', 'nicknames'])
        nicknames = profile['nicknames'] if 'nicknames' in profile else []
        existing_spellings = set(nicknames)
        for key in {'first_name', 'last_name', 'maiden_name'}:
            if key in profile:
                existing_spellings.add(profile[key])
        leftover_spellings = self.spellings.difference(existing_spellings)
        if not leftover_spellings:
            return None
        nicknames.extend(leftover_spellings)
        return Update(message=f"{profile_id} {profile['name']} ({existing_spellings}): {nicknames}",
                      update=(NicknameUpdate(profile_id, nicknames)))

    def do_update(self, update: NicknameUpdate):
        self.geni_api.update_profile(update.profile_id, {'nicknames': ','.join(update.nicknames)})


if __name__ == '__main__':
    geni_api = GeniApi()
    my_family = geni_api.get_immediate_family('profile-g6000000002032852714')
    family_members = [item['id'] for sublist in my_family.values() for item in sublist]
    update_items(SpellingUpdater(geni_api, spellings={'Holczer', 'Holzer'}), family_members)

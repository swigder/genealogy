from collections import namedtuple
from typing import Set, Optional, List

from geni_api import GeniApi
from update_lib import update_items, Update, Updater

NicknameUpdate = namedtuple('NicknameUpdate', ['profile_id', 'nicknames'])


class SpellingUpdater(Updater):
    def __init__(self, geni_api: GeniApi, spellings: Set[str], secondary_spellings: Set[str]=None):
        self.geni_api = geni_api
        self.spellings = spellings
        self.all_spellings = self.spellings.union(secondary_spellings or {})

    def get_updates(self, profile_ids: List[str]) -> List[Optional[Update]]:
        profiles = self.geni_api.get_profiles(profile_ids,
                                              fields=['id', 'name', 'first_name', 'maiden_name', 'last_name',
                                                      'nicknames'])
        updates = []
        if 'results' not in profiles:
            print(profiles)
            return []
        for profile in profiles['results']:
            nicknames = profile['nicknames'] if 'nicknames' in profile else []
            existing_spellings = set(nicknames)
            for key in {'first_name', 'last_name', 'maiden_name'}:
                if key in profile:
                    existing_spellings.add(profile[key])
            if not existing_spellings.intersection(self.all_spellings):
                continue
            leftover_spellings = self.spellings.difference(existing_spellings)
            if not leftover_spellings:
                continue
            nicknames.extend(leftover_spellings)
            updates.append(Update(message=f"{profile['id']} {profile['name']} ({existing_spellings}): {nicknames}",
                                  update=(NicknameUpdate(profile['id'], nicknames))))
        return updates

    def do_update(self, update: NicknameUpdate):
        self.geni_api.update_profile(update.profile_id, {'nicknames': ','.join(update.nicknames)})


if __name__ == '__main__':
    geni_api = GeniApi()
    my_managed_profiles = geni_api.get_managed_profiles(fields=['id'])
    ids = [f'{profile["id"]}' for profile in my_managed_profiles]
    update_items(SpellingUpdater(geni_api, spellings={'Friedman'}, secondary_spellings={'Friedmann'}), ids, batch_size=30)

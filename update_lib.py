from collections import namedtuple
from typing import List

Update = namedtuple('Update', ['message', 'update'])


class Updater:
    def get_update(self, key: str):
        pass

    def do_update(self, update):
        pass


def update_items(updater, items) -> List:
    update_confirmation = 'r'
    updates = []

    while update_confirmation == 'r':
        updates = [updater.get_update(item) for item in items]
        updates = list(filter(None, updates))

        if not updates:
            update_confirmation = input('No updates found! [r]etry/[E]xit').lower().strip()
            continue

        for update in updates:
            print(update.message)

        update_confirmation = input("Confirm [y]es/[r]etry/[N]o]").lower().strip()

    update_confirmed = update_confirmation == 'y'

    if not update_confirmed:
        print('Cancelling...')
        return []

    if update_confirmed:
        print(f'Continuing with {len(updates)} updates...')
        try:
            results = [updater.do_update(update.update) for update in updates]
        except Exception as e:
            print(e)
            raise
        print('Done.')
        return results

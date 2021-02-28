from collections import namedtuple
from typing import List, Optional

Update = namedtuple('Update', ['message', 'update'])


class Updater:
    def get_updates(self, keys: List[str]) -> List[Optional[Update]]:
        return [self.get_update(key) for key in keys]

    def get_update(self, key: str) -> Optional[Update]:
        updates = self.get_updates([key])
        return updates[0] if updates else None

    def do_update(self, update):
        pass


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def update_items(updater, items, batch_size=1) -> List:
    update_confirmation = 'r'
    updates = []

    while update_confirmation == 'r':
        if batch_size > 1:
            updates = [updater.get_updates(item) for item in chunks(items, batch_size)]
            updates = [item for sublist in updates for item in sublist]
        else:
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

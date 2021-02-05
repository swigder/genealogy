from collections import namedtuple

Update = namedtuple('Update', ['message', 'update'])


class Updater:
    def get_update(self, key: str):
        pass

    def do_update(self, update):
        pass


def update_items(updater, items):
    updates = [updater.get_update(item) for item in items]
    updates = list(filter(None, updates))

    if not updates:
        print('No updates found!')
        return

    for update in updates:
        print(update.message)

    update_confirmed = input("Confirm [y/N]").lower().strip() == 'y'

    if not update_confirmed:
        print('Cancelling...')
        return

    if update_confirmed:
        print(f'Continuing with {len(updates)} updates...')
        for update in updates:
            updater.do_update(update.update)
        print('Done.')

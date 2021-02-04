from collections import namedtuple

Update = namedtuple('Update', ['message', 'update'])


def update_items(items, get_update_fn, do_update_fn):
    updates = [get_update_fn(item) for item in items]
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
            do_update_fn(update)
        print('Done.')

from datetime import datetime

from geni_family_tree import GeniFamilyTreeGenerator

start = datetime.now()

generator = GeniFamilyTreeGenerator()
family_tree = generator.generate_tree(max_depth=10)
# family_tree.print_tree()
print('\nFamily names:\n', '\n '.join(family_tree.family_names()))

stop = datetime.now()
print('\nTime elapsed:', (stop-start).total_seconds(), 'seconds')

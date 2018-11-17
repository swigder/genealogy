from collections import namedtuple

from anytree import RenderTree

Person = namedtuple('Person', ('data', 'ancestors', 'descendants'))
PersonData = namedtuple('PersonData', ('id', 'first_name', 'last_name', 'display_name'))


class FamilyTree:
    def __init__(self, root, people=None):
        self.root = root
        self.people = {} if not people else people

    def print_tree(self):
        for pre, fill, node in RenderTree(self.people[self.root].ancestors):
            print("%s%s" % (pre, self.people[node.name].data.display_name))

    def family_names(self):
        return sorted({v.data.last_name for v in self.people.values()})

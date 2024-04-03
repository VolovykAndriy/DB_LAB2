import sys
import random


def hash_name(s: str) -> int:
    result = 0
    scale = sys.maxsize
    s = s.lower()
    padding = 'z' * (3 - len(s) % 3)
    s += padding
    for i in range(0, len(s), 3):
        trigram = s[i:i + 3]
        index = sum([(ord(char.lower()) - ord('a') + 1 if char.isalpha() else 0) * 26 ** pos for pos, char in
                     enumerate(reversed(trigram))])
        result += index * scale
        scale //= 26 ** 3
    return result


class Node(object):
    def __init__(self, parent=None):
        self.keys: list = []
        self.values: list[Node] = []
        self.parent: Node = parent

    def index(self, key: int) -> int:
        for i, item in enumerate(self.keys):
            if key < item:
                return i

        return len(self.keys)

    def __getitem__(self, item):
        return self.values[self.index(item)]

    def __setitem__(self, key: int = None, value: str = ''):
        key = hash_name(value) if key is None else key
        i = self.index(key)
        self.keys[i:i] = [key]
        self.values.pop(i)
        self.values[i:i] = value

    def split(self) -> (int, list):
        left = Node(self.parent)

        mid = len(self.keys) // 2

        left.keys = self.keys[:mid]
        left.values = self.values[:mid + 1]
        for child in left.values:
            child.parent = left

        key = self.keys[mid]
        self.keys = self.keys[mid + 1:]
        self.values = self.values[mid + 1:]

        return key, [left, self]

    def __delitem__(self, key):
        i = self.index(key)
        del self.values[i]
        if i < len(self.keys):
            del self.keys[i]
        else:
            del self.keys[i - 1]

    def fusion(self):

        index = self.parent.index(self.keys[0])
        if index < len(self.parent.keys):
            next_node: Node = self.parent.values[index + 1]
            next_node.keys[0:0] = self.keys + [self.parent.keys[index]]
            for child in self.values:
                child.parent = next_node
            next_node.values[0:0] = self.values
        else:
            prev: Node = self.parent.values[-2]
            prev.keys += [self.parent.keys[-1]] + self.keys
            for child in self.values:
                child.parent = prev
            prev.values += self.values

    def borrow_key(self, minimum: int) -> bool:
        index = self.parent.index(self.keys[0])
        if index < len(self.parent.keys):
            next_node: Node = self.parent.values[index + 1]
            if len(next_node.keys) > minimum:
                self.keys += [self.parent.keys[index]]

                borrow_node = next_node.values.pop(0)
                borrow_node.parent = self
                self.values += [borrow_node]
                self.parent.keys[index] = next_node.keys.pop(0)
                return True
        elif index != 0:
            prev: Node = self.parent.values[index - 1]
            if len(prev.keys) > minimum:
                self.keys[0:0] = [self.parent.keys[index - 1]]

                borrow_node = prev.values.pop()
                borrow_node.parent = self
                self.values[0:0] = [borrow_node]
                self.parent.keys[index - 1] = prev.keys.pop()
                return True

        return False


class Leaf(Node):
    def __init__(self, parent=None, prev_node=None, next_node=None):
        super(Leaf, self).__init__(parent)
        self.next: Leaf = next_node
        if next_node is not None:
            next_node.prev = self
        self.prev: Leaf = prev_node
        if prev_node is not None:
            prev_node.next = self

    def __getitem__(self, item):
        return self.values[self.keys.index(item)]

    def __setitem__(self, key: int = None, value: str = ''):
        key = hash_name(value) if key is None else key
        i = self.index(key)
        self.keys.insert(i, key)
        self.values.insert(i, value)

    def split(self):

        left = Leaf(self.parent, self.prev, self)
        mid = len(self.keys) // 2

        left.keys = self.keys[:mid]
        left.values = self.values[:mid]

        self.keys: list = self.keys[mid:]
        self.values: list = self.values[mid:]

        return self.keys[0], [left, self]

    def __delitem__(self, key):
        i = self.keys.index(key)
        del self.keys[i]
        del self.values[i]

    def fusion(self):
        if self.next is not None and self.next.parent == self.parent:
            self.next.keys[0:0] = self.keys
            self.next.values[0:0] = self.values
        else:
            self.prev.keys += self.keys
            self.prev.values += self.values

        if self.next is not None:
            self.next.prev = self.prev
        if self.prev is not None:
            self.prev.next = self.next

    def borrow_key(self, minimum: int):
        index = self.parent.index(self.keys[0])
        if index < len(self.parent.keys) and len(self.next.keys) > minimum:
            self.keys += [self.next.keys.pop(0)]
            self.values += [self.next.values.pop(0)]
            self.parent.keys[index] = self.next.keys[0]
            return True
        elif index != 0 and len(self.prev.keys) > minimum:
            self.keys[0:0] = [self.prev.keys.pop()]
            self.values[0:0] = [self.prev.values.pop()]
            self.parent.keys[index - 1] = self.keys[0]
            return True

        return False

    def values_greater_than(self, key):
        index = self.index(key)
        return [self.values[i] for i in range(index, len(self.keys))]

    def values_less_than(self, key):
        index = self.index(key)
        return [self.values[i] for i in range(index - 1)]


class BPlusTree(object):
    root: Node

    def __init__(self, maximum=4):
        self.root = Leaf()
        self.maximum: int = maximum if maximum > 2 else 2
        self.minimum: int = self.maximum // 2
        self.depth = 0

    def find(self, key) -> Node:
        node = self.root
        while type(node) is not Leaf:
            node = node[key]

        return node

    def __getitem__(self, item):
        return self.find(item)[item]

    def __setitem__(self, key, value, leaf=None):
        if leaf is None:
            leaf = self.find(key)
        leaf[key] = value
        if len(leaf.keys) > self.maximum:
            self.insert_index(*leaf.split())

    def insert(self, name: str = '', phone: str = ''):
        key = hash_name(name)
        value = (name, phone)
        leaf = self.find(key)
        self.__setitem__(key, value, leaf)

    def insert_index(self, key, values: list[Node]):
        parent = values[1].parent
        if parent is None:
            values[0].parent = values[1].parent = self.root = Node()
            self.depth += 1
            self.root.keys = [key]
            self.root.values = values
            return

        parent[key] = values
        if len(parent.keys) > self.maximum:
            self.insert_index(*parent.split())

    def delete(self, name: str = "", key: int = None, node: Node = None):
        key = hash_name(name) if key is None else key
        if node is None:
            node = self.find(key)
        del node[key]

        if len(node.keys) < self.minimum:
            if node == self.root:
                if len(self.root.keys) == 0 and len(self.root.values) > 0:
                    self.root = self.root.values[0]
                    self.root.parent = None
                    self.depth -= 1
                return

            elif not node.borrow_key(self.minimum):
                node.fusion()
                self.delete("", key, node.parent)

    def show(self, node=None, file=None, _prefix="", _last=True):
        if node is None:
            node = self.root
        if type(node) is Leaf:
            print(_prefix, "`- " if _last else "|- ", node.keys, ":", node.values, sep="", file=file)
        else:
            print(_prefix, "`- " if _last else "|- ", node.keys, sep="", file=file)
            _prefix += "   " if _last else "|  "

            for i, child in enumerate(node.values):
                _last = (i == len(node.values) - 1)
                self.show(child, file, _prefix, _last)

    def search(self, name: str = "", key: int = None):
        key = hash_name(name) if key is None else key
        leaf = self.find(key)
        if key in leaf.keys:
            return leaf[key]
        else:
            return None

    def search_greater_than(self, name: str, key: int = None):
        key = hash_name(name) if key is None else key
        leaf = self.find(key)
        results = []
        results.extend(leaf.values_greater_than(key))
        node = leaf.next
        while node is not None:
            results.extend(node.values)
            node = node.next
        return results

    def search_less_than(self, name: str, key: int = None):
        key = hash_name(name) if key is None else key
        leaf = self.find(key)
        results = []
        results.extend(leaf.values_less_than(key))
        node = leaf.prev
        while node is not None:
            results.extend(node.values)
            node = node.prev
        return results


def demo():
    names = ['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot', 'Golf', 'Hotel', 'India', 'Juliet', 'Kilo',
             'Lima', 'Mike', 'November', 'Oscar', 'Papa', 'Quebec', 'Romeo', 'Sierra', 'Tango', 'Uniform', 'Victor',
             'Whiskey', 'X-ray', 'Yankee', 'Zulu']
    phone_numbers = ['+380' + ''.join(str(random.randint(0, 9)) for _ in range(9)) for _ in range(10)]
    bplustree = BPlusTree()
    random_list = random.sample(names, 10)
    print("_" * 50 + "Random Insert" + "_" * 50)
    for name, phone_number in zip(random_list, phone_numbers):
        bplustree.insert(name, phone_number)
        print('Insert ' + name + " " + phone_number)
        bplustree.show()
    print("_" * 50 + "Random Search" + "_" * 50)
    random.shuffle(random_list)
    random_search = random.sample(random_list, 3)
    for name in random_search:
        print(f"Search {name}", bplustree.search(name))
        print(f"Search before {name}", bplustree.search_less_than(name))
        print(f"Search after {name}", bplustree.search_greater_than(name))

    print("_" * 50 + "Random Delete" + "_" * 50)
    random.shuffle(random_list)
    for i in random_list:
        print('Delete ' + i)
        bplustree.delete(i)
        bplustree.show()


if __name__ == "__main__":
    demo()
    # names = ['Abigail Alpha', 'Ben Bravo', 'Courtney Charlie', 'David Delta', 'Eline Echo', 'Frank Foxtrot',
    #          'Greg Golf',
    #          'Harper Hotel', 'Ivy India', 'John Juliet', 'Kevin Kilo', 'Logan Lima', 'Mary Mike', 'Noah November',
    #          'Olivia Oscar', 'Patrick Papa', 'Quentin Quebec', 'Robert Romeo', 'Sara Sierra', 'Timmy Tango',
    #          'Ursule Uniform', 'Vincent Victor', 'Wendy Whiskey', 'Xavier X-ray', 'Yonatan Yankee', 'Zoe Zulu',
    #          'Abigail Alpha', 'Ben Bravo', 'Courtney Charlie', 'David Delta', 'Eline Echo', 'Frank Foxtrot',
    #          'Greg Golf',
    #          'Harper Hotel', 'Ivy India', 'John Juliet', 'Kevin Kilo', 'Logan Lima', 'Mary Mike', 'Noah November',
    #          'Olivia Oscar', 'Patrick Papa', 'Quentin Quebec', 'Robert Romeo', 'Sara Sierra', 'Timmy Tango',
    #          'Ursule Uniform', 'Vincent Victor', 'Wendy Whiskey', 'Xavier X-ray', 'Yonatan Yankee', 'Zoe Zulu']
    #
    # bplustree = BPlusTree()
    # for name in names:
    #     bplustree.insert(name)
    #
    # bplustree.show()

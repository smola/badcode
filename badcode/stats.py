
import pickle
import typing

import bblfsh

class Stats:
    def __init__(self) -> None:
        self.data: typing.Dict[bblfsh.Node,int] = {}

    def added(self, tree: bblfsh.Node) -> None:
        ser = tree.SerializeToString()
        if ser not in self.data:
            self.data[ser] = {'added': 0, 'deleted': 0}
        self.data[ser]['added'] += 1

    def deleted(self, tree: bblfsh.Node) -> None:
        ser = tree.SerializeToString()
        if ser not in self.data:
            self.data[ser] = {'added': 0, 'deleted': 0}
        self.data[ser]['deleted'] += 1

    def save(self) -> None:
        with open('stats.db', 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load() -> 'Stats':
        with open('stats.db', 'rb') as f:
            return pickle.load(f)


import pickle
import typing

import bblfsh

class Stats:
    def __init__(self) -> None:
        self.data: typing.Dict[bblfsh.Node,int] = {}

    def add(self, tree: bblfsh.Node) -> None:
        self.data[tree] = self.data.get(tree, 0) + 1

    def save(self) -> None:
        with open('stats.db', 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load() -> 'Stats':
        with open('stats.db', 'rb') as f:
            return pickle.load(f)

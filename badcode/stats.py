
import os.path
import pickle
import typing

import bblfsh

from .bblfsh import Snippet

DEFAULT_STATS_DB = 'stats.db'

class Stats:
    def __init__(self) -> None:
        self.totals: typing.Dict[Snippet,typing.Dict[str,int]] = {}
        self.per_repo: typing.Dict[str,typing.Dict[Snippet,typing.Dict[str,int]]] = {}

    def added(self, repo: str, element: Snippet) -> None:
        self._add(repo, element, 'added')

    def deleted(self, repo: str, element: bblfsh.Node) -> None:
        self._add(repo, element, 'deleted')

    def _add(self, repo: str, element: Snippet, key: str) -> None:
        if element not in self.totals:
            self.totals[element] = {'added': 0, 'deleted': 0}
        self.totals[element][key] += 1
        if repo not in self.per_repo:
            self.per_repo[repo] = {}
        if element not in self.per_repo[repo]:
            self.per_repo[repo][element] = {'added': 0, 'deleted': 0}
        self.per_repo[repo][element][key] += 1

    def save(self, filename=DEFAULT_STATS_DB) -> None:
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load(filename=DEFAULT_STATS_DB) -> 'Stats':
        with open(filename, 'rb') as f:
            return pickle.load(f)

    @staticmethod
    def load_or_create(filename=DEFAULT_STATS_DB) -> 'Stats':
        if os.path.exists(filename):
            return Stats.load(filename)
        return Stats()
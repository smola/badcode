
import collections
import os.path
import pickle
import typing

import bblfsh

from .bblfsh import Snippet

DEFAULT_STATS_DB = 'stats.db'

class Stats:
    def __init__(self) -> None:
        self.totals = {}
        self.per_repo = {}

    def added(self, repo: str, element: Snippet) -> None:
        self._add(repo, element, 'added')

    def deleted(self, repo: str, element: bblfsh.Node) -> None:
        self._add(repo, element, 'deleted')

    def _add(self, repo: str, element: Snippet, key: str) -> None:
        if element not in self.totals:
            self.totals[element] = collections.defaultdict(int)
        self.totals[element][key] += 1
        if repo not in self.per_repo:
            self.per_repo[repo] = {}
        if element not in self.per_repo[repo]:
            self.per_repo[repo][element] = {'added': 0, 'deleted': 0}
        self.per_repo[repo][element][key] += 1

    def __iadd__(self, other: 'Stats') -> 'Stats':
        self._merge_dict_of_dicts_of_int_values(
            self.totals,
            other.totals)
        for repo, val in other.per_repo.items():
            if repo not in self.per_repo:
                self.per_repo[repo] = {}
            self._merge_dict_of_dicts_of_int_values(
                self.per_repo[repo], val)
        return self

    def _merge_dict_of_dicts_of_int_values(self, a, b):
        for key, val in b.items():
            prev = a.get(key, collections.defaultdict(int))
            a[key] = self._merge_dict_of_int_values(prev, val)

    def _merge_dict_of_int_values(self, a, b):
        c = collections.defaultdict(int)
        for k, v in a.items():
            c[k] += v
        for k, v in b.items():
            c[k] += v
        return c

    def merge_snippet(self, dst: Snippet, src: Snippet, positive: bool) -> None:
        self._merge_stats(self.totals, dst, src, positive)
        for d in self.per_repo.values():
            self._merge_stats(d, dst, src, positive)

    def _merge_stats(self, d, dst: Snippet, src: Snippet, positive: bool) -> None:
        if src not in d:
            return
        dst_stats = d.get(dst, collections.defaultdict(int))
        src_stats = d[src]
        dst_stats['added'] += src_stats['added']
        dst_stats['deleted'] += src_stats['deleted']
        if positive:
            dst_stats['merged_positive'] += 1
        else:
            dst_stats['merged_negative'] += 1
        dst_stats['merged'] += 1
        d[dst] = dst_stats

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
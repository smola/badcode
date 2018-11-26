
import collections
import os.path
import pickle
from typing import Optional, Tuple, Union

import bblfsh

from .bblfshutil import UAST

DEFAULT_STATS_DB = 'stats.db'

class Stats:
    def __init__(self) -> None:
        self.text = {}
        self.totals = {}
        self.per_repo = {}

    def added(self, repo: str, uast: UAST, text: str) -> None:
        self._add(repo, uast, text, 'added')

    def deleted(self, repo: str, uast: UAST, text: str) -> None:
        self._add(repo, uast, text, 'deleted')

    def _add(self, repo: str, uast: UAST, text: str, key: str) -> None:
        if uast not in self.text:
            self.text[uast] = text
        if uast not in self.totals:
            self.totals[uast] = collections.defaultdict(int)
        self.totals[uast][key] += 1
        if repo not in self.per_repo:
            self.per_repo[repo] = {}
        if uast not in self.per_repo[repo]:
            self.per_repo[repo][uast] = {'added': 0, 'deleted': 0}
        self.per_repo[repo][uast][key] += 1

    def __iadd__(self, other: 'Stats') -> 'Stats':
        self._merge_dict_of_dicts_of_int_values(
            self.totals,
            other.totals)
        for repo, val in other.per_repo.items():
            if repo not in self.per_repo:
                self.per_repo[repo] = {}
            self._merge_dict_of_dicts_of_int_values(
                self.per_repo[repo], val)
        for uast, text in other.text.items():
            if uast not in self.text:
                self.text[uast] = text
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

    def merge_uast(self, dst: UAST, src: UAST) -> None:
        self._merge_stats(self.totals, dst, src)
        for d in self.per_repo.values():
            self._merge_stats(d, dst, src)
        if dst not in self.text:
            self.text[dst] = self.text[src]

    def _merge_stats(self, d, dst: UAST, src: UAST) -> None:
        if src not in d:
            return
        positive = d[src]['added'] >= d[src]['deleted']            
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

    def match(self, uast: UAST) -> Optional[Tuple[UAST,str]]:
        for s in self.totals:
            if s.match(uast):
                return (s, self.text[s])
        return None

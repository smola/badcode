
import math

import math
import sys
import typing

from badcode.stats import *
from badcode.bblfsh import *
from badcode.treedist import node_distance
from badcode.treedist import node_merge

import bblfsh


def simple_score(s):
    total = float(s['added']+s['deleted'])
    return s['deleted'] / total

def score(stats: Stats, key: Snippet) -> float:
    s = stats.totals[key]
    n_repos = len([1 for d in stats.per_repo.values() if key in d])
    total_repos = len(stats.per_repo)
    pct_repo = float(n_repos) / total_repos
    
    total = float(s['added']+s['deleted'])
    return math.log(pct_repo*100) * s['deleted'] / total

def print_top(stats: Stats) -> None:
    top = list(reversed(sorted(stats.totals.keys(), key=lambda x: score(stats, x))))
    top = top[:10]
    print('TOTAL: %d' % len(stats.totals))
    for n, s in enumerate(top):
        print('--- SNIPPET %d ---' % n)
        print('STATS: %s' % stats.totals[s])
        print('REPOS: %d' % len([1 for d in stats.per_repo.values() if s in d]))
        print('SCORE: %f' % score(stats, s))
        print(s.text)
        #print(s.uast)
        print()

def merge_same_text(stats: Stats) -> None:
    per_text = {}
    for snippet, st in stats.totals.items():
        if snippet.text not in per_text:
            per_text[snippet.text] = (snippet, st)
        else:
            if uast_size(snippet.uast) > uast_size(per_text[snippet.text][0].uast):
                per_text[snippet.text] = (snippet, st)
    stats.totals = dict(per_text.values())

def merge_similar(stats: Stats) -> None:
    candidates = set([])
    for snippet, sstats in stats.totals.items():
        if sstats['deleted'] >= sstats['added']:
            candidates.add(id(snippet))
    all_pairs = list(stats.totals.items())
    merged_items = {}
    for n, ss in enumerate(all_pairs):
        snippet = ss[0]
        sstats = ss[1]
        if id(snippet) not in candidates:
            continue
        for osnippet, osstats in all_pairs[n+1:]:
            if id(snippet) == id(osnippet):
                continue
            if id(osnippet) not in candidates:
                continue
            if abs(simple_score(sstats) - simple_score(osstats)) >= 0.2:
                continue
            merged = node_merge(snippet.uast, osnippet.uast, max_dist=1)
            if merged is None:
                continue
            merged_snippet = Snippet(uast=merged, text=snippet.text)
            if merged_snippet not in merged_items:
                merged_items[merged_snippet] = set([])
            merged_items[merged_snippet].add(snippet)
            merged_items[merged_snippet].add(osnippet)
    for snippet, lst in merged_items.items():
        s = {'added': 0, 'deleted': 0}
        for snpt in lst:
            st = stats.totals[snpt]
            s['added'] += st['added']
            s['deleted'] += st['deleted']
        s['merged'] = len(lst)
        stats.totals[snippet] = s

def postprocess(path: str):
    stats = Stats.load(filename=path)
    print('--- NO POSTPROCESSING ---')
    print_top(stats)

    print('--- POSTPROCESSING (merge same text) ---')
    merge_same_text(stats)
    print_top(stats)

    print('--- POSTPROCESSING (merge similars) ---')
    merge_similar(stats)
    print_top(stats)

def main():
    bblfsh_monkey_patch()
    postprocess(sys.argv[1])
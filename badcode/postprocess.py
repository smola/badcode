
import math

import math
import sys
import typing

from badcode.stats import *
from badcode.bblfsh import *

import bblfsh

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

def postprocess(path: str):
    stats = Stats.load(filename=path)
    print('--- NO POSTPROCESSING ---')
    print_top(stats)
    
    merge_same_text(stats)
    
    print('--- POSTPROCESSING (merge same text) ---')
    print_top(stats)

def main():
    bblfsh_monkey_patch()
    postprocess(sys.argv[1])
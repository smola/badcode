
import math
import sys
import typing

from badcode.stats import *
from badcode.bblfsh import *
from badcode.treedist import node_distance
from badcode.treedist import fast_distance
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
    # TODO: currently fails on merged nodes
    #return math.log(pct_repo*100) * s['deleted'] / total
    return math.log(total) * s['deleted'] / total

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

def _candidates_for_merge(stats: Stats) -> typing.Generator[typing.Tuple[Snippet, Snippet],None,None]:
    candidates = []
    sizes = {}
    scores = {}
    for snippet, sstats in stats.totals.items():
        if sstats['deleted'] < sstats['added']:
            continue
        size = uast_size(snippet.uast)
        if size > 10:
            continue
        candidates.append(snippet)
        sizes[id(snippet)] = size
        scores[id(snippet)] = simple_score(sstats)
    all_pairs = list(stats.totals.items())
    proc = 0
    total_candidates = len(candidates)
    for n, snippet in enumerate(candidates):
        proc += 1
        if proc % 1000 == 0:
            print('Candidates processed: %d/%d' % (proc, total_candidates))
        i1 = id(snippet)
        for osnippet in candidates[n+1:]:
            i2 = id(osnippet)
            if i1 == i2:
                continue
            if sizes[i1] != sizes[i2]:
                continue
            if abs(scores[i1] - scores[i2]) >= 0.1:
                continue
            yield (snippet, osnippet)

def _merge_worker(x):
    merged_node = node_merge(x[0].uast, x[1].uast, max_dist=1)
    if merged_node is None:
        return (None, None, None)
    snippet, osnippet = x[0], x[1]
    merged_snippet = Snippet(uast=merged_node, text=snippet.text)
    return (merged_snippet, snippet, osnippet)

def merge_similar(stats: Stats) -> None:
    merged_items = {}
    candidates = _candidates_for_merge(stats)
    proc = 0
    procm = 0
    merged = map(_merge_worker, candidates)
    for merged_snippet, snippet, osnippet in merged: 
        proc += 1
        if proc % 10000 == 0:
            print('Processed: (%d, %d)' % (proc, procm))
        if merged_snippet is None:
            continue
        procm += 1
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
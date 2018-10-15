
import math
import sys
import typing

from badcode.stats import *
from badcode.bblfsh import *
from badcode.treedist import node_distance
from badcode.treedist import fast_distance
from badcode.treedist import node_merge
from badcode.treedist import single_node_merge
from badcode.treedist import single_node_merge_precalc
from badcode.treedist import TreeToSeq

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

def merge_similar(stats: Stats) -> None:
    merged_snippets = {}
    snippets = []
    tts = TreeToSeq()
    for snippet, sstats in stats.totals.items():
        single_node = len(snippet.uast.children) == 0
        tree_seq = tts.tree_to_seq(snippet.uast)
        snippets.append((snippet, sstats, tree_seq, single_node))
    tts = None
    total = len(snippets)
    proc = 0
    for i, (snippet, sstats, tree_seq, single_node) in enumerate(snippets):
        if proc % 1000 == 0:
            print('Processed: %d/%d)' % (proc, total))
        proc += 1
        if single_node:
            continue
        if sstats['added'] >= sstats['deleted']:
            continue
        for osnippet, osstats, otree_seq, osingle_node in snippets[i+1:]:
            if osingle_node:
                continue
            if osstats['added'] >= osstats['deleted']:
                continue
            merged_uast = single_node_merge_precalc(snippet.uast, osnippet.uast, tree_seq, otree_seq)
            if merged_uast is None:
                continue
            merged_snippet = Snippet(uast=merged_uast, text=snippet.text)
            lst = merged_snippets.get(merged_snippet, set([]))
            lst.add(snippet)
            lst.add(osnippet)
            merged_snippets[merged_snippet] = lst

    for snippet, lst in merged_snippets.items():
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
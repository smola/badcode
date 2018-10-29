
import collections
import math
import sys
import typing

from badcode.stats import *
from badcode.bblfsh import *
from badcode.ranker import Ranker
from badcode.treedist import node_distance
from badcode.treedist import fast_distance
from badcode.treedist import node_merge
from badcode.treedist import single_node_merge
from badcode.treedist import single_node_merge_precalc
from badcode.treedist import TreeToSeq

import bblfsh


def score1(stats: Stats, key: Snippet) -> float:
    s = stats.totals[key]
    total = float(s['added']+s['deleted'])
    return s['deleted'] / total

def score2(stats: Stats, key: Snippet) -> float:
    s = stats.totals[key]
    total = float(s['added']+s['deleted'])
    return math.log(total+1) * s['deleted'] / total

def score3(stats: Stats, key: Snippet) -> float:
    s = stats.totals[key]
    total_repos = len(stats.per_repo)
    n_repos = 0
    neg_repos = 0
    for d in stats.per_repo.values():
        if key not in d:
            continue
        n_repos += 1
        s = d[key]
        if s['deleted'] >= s['added']:
            neg_repos += 1
    return math.log(n_repos+1) / math.log(total_repos + 1) * neg_repos / n_repos

def print_top(stats: Stats) -> None:
    rankers = [
        Ranker(lambda x: score1(stats, x)),
        Ranker(lambda x: score2(stats, x)),
        Ranker(lambda x: score3(stats, x))
    ]
    
    for s in stats.totals:
        for r in rankers:
            r.add(s)

    for r in rankers:
        r.finalize()

    ranker = rankers[2]

    top = list(reversed(sorted(stats.totals.keys(), key=lambda x: ranker.get(x))))
    top = top[:10]
    print('TOTAL: %d' % len(stats.totals))
    for n, s in enumerate(top):
        print('--- SNIPPET %d ---' % n)
        print('STATS: %s' % stats.totals[s])
        print('REPOS: %d' % len([1 for d in stats.per_repo.values() if s in d]))
        for i, ranker in enumerate(rankers):
            print('SCORE%d: %f' % (i+1, ranker.get(s)))
        print('TEXT:')
        print(s.text)
        print('UAST:')
        print(s.uast)
        print()

def merge_same_text(stats: Stats) -> None:
    #FIXME: does not merge per_repo
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
    merged_sizes = {}
    snippets = []
    positive_snippets = []
    tts = TreeToSeq()
    for snippet, sstats in stats.totals.items():
        uast = snippet.uast
        if len(uast.children) == 0:
            continue
        tree_seq = tts.tree_to_seq(uast)
        if sstats['added'] >= sstats['deleted']:
            positive_snippets.append((snippet, sstats, tree_seq, uast))
        else:
            snippets.append((snippet, sstats, tree_seq, uast))
    tts = None
    total = len(snippets)
    proc = 0
    for i, (snippet, sstats, tree_seq, uast) in enumerate(snippets):
        if proc % 1000 == 0:
            print('Processed: %d/%d)' % (proc, total))
        proc += 1
        for osnippet, osstats, otree_seq, ouast in snippets[i+1:]:
            merged_uast = single_node_merge_precalc(uast, ouast, tree_seq, otree_seq)
            if merged_uast is None:
                continue
            merged_snippet = Snippet(uast=merged_uast, text='MERGED: ' + snippet.text)
            lst = merged_snippets.get(merged_snippet, set([]))
            lst.add(snippet)
            lst.add(osnippet)
            merged_snippets[merged_snippet] = lst
            merged_sizes[merged_snippet] = len(tree_seq)

    for snippet, lst in merged_snippets.items():
        for snpt in lst:
            stats.merge_snippet(dst=snippet, src=snpt, positive=False)
        uast_size = merged_sizes[snippet]
        for snpt in positive_snippets:
            if uast_size != len(snpt[2]):
                continue
            if uast_eq_wildcards(snippet.uast, snpt[3]):
                st = stats.totals[snpt[0]]
                stats.merge_snippet(dst=snippet, src=snpt[0], positive=True)

def postprocess(path: str):
    stats = Stats.load(filename=path)
    #print('--- NO POSTPROCESSING ---')
    #print_top(stats)

    #print('--- POSTPROCESSING (merge same text) ---')
    #merge_same_text(stats)
    #print_top(stats)

    print('--- POSTPROCESSING (merge similars) ---')
    merge_similar(stats)
    print_top(stats)

def main():
    bblfsh_monkey_patch()
    postprocess(sys.argv[1])
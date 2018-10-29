
import collections
import math
import os.path
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
    if s['added'] > s['deleted']:
        return 0.0

    if 'merged' in s:
        if s['merged_positive'] >= s['merged_negative']:
            return 0.0

    total = float(s['added']+s['deleted'])
    return math.log(total+1) * s['deleted'] / total

def score2(stats: Stats, key: Snippet) -> float:
    s = stats.totals[key]
    if s['added'] > s['deleted']:
        return 0.0

    if 'merged' in s:
        if s['merged_positive'] >= s['merged_negative']:
            return 0.0

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

    if neg_repos <= (n_repos - neg_repos):
        return 0.0

    return math.log(n_repos+1) / math.log(total_repos + 1) * neg_repos / n_repos

def score_avg(stats: Stats, key: Snippet) -> float:
    s = stats.totals[key]
    scores = [v for k, v in s.items() if k.startswith('score_')]
    return float(sum(scores)) / len(scores)

def compute_ranking(stats: Stats) -> None:
    rankers = [
        Ranker(lambda x: score1(stats, x)),
        Ranker(lambda x: score2(stats, x)),
    ]
    
    for s in stats.totals:
        for r in rankers:
            r.add(s)

    for r in rankers:
        r.finalize()

    for snpt in stats.totals:
        s = stats.totals[snpt]
        for i, r in enumerate(rankers):
            s['score_%d' % (i+1)] = r.get(snpt)

    rankers = None
    r = Ranker(lambda x: score_avg(stats, x))
    for s in stats.totals:
        r.add(s)
    r.finalize()
    for snpt in stats.totals:
        s = stats.totals[snpt]
        s['score'] = r.get(snpt)

def prune(stats: Stats, min_score: float) -> None:
    stats.totals = dict([(k, v) for k, v in stats.totals.items() if v['score'] >= min_score])
    for d in stats.per_repo.values():
        for snpt in list(d.keys()):
            if snpt not in stats.totals:
                del d[snpt]

def print_top(stats: Stats, k: int) -> None:
    top = list(reversed(sorted(stats.totals.keys(), key=lambda x: stats.totals[x]['score'])))
    top = top[:k]
    print('TOTAL: %d' % len(stats.totals))
    for n, s in enumerate(top):
        print('--- SNIPPET %d ---' % n)
        print('STATS: %s' % stats.totals[s])
        print('REPOS: %d' % len([1 for d in stats.per_repo.values() if s in d]))
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
    merged_path = path + '_merged'
    ranked_path = merged_path + '_ranked'
    pruned_path = ranked_path + '_pruned'

    stats = None
    print('--- LOADING STATS ---')

    #print('--- NO POSTPROCESSING ---')
    #print_top(stats)

    #print('--- POSTPROCESSING (merge same text) ---')
    #merge_same_text(stats)
    #print_top(stats)

    if not os.path.exists(merged_path):
        if stats is None:
            stats = Stats.load(filename=path)
        print('--- POSTPROCESSING (merge similars) ---')
        merge_similar(stats)
        stats.save(filename=merged_path)
    
    if not os.path.exists(ranked_path):
        if stats is None:
            stats = Stats.load(filename=merged_path)
        print('--- RANKING ---')
        compute_ranking(stats)
        stats.save(filename=ranked_path)

    if not os.path.exists(pruned_path):
        if stats is None:
            stats = Stats.load(filename=ranked_path)
        min_score = 0.98
        print('--- PRUNING ---')
        print('MIN_SCORE: %f' % min_score)
        print('BEFORE: %d' % len(stats.totals))
        prune(stats, min_score=min_score)
        compute_ranking(stats)
        print('AFTER: %d' % len(stats.totals))
        stats.save(filename=pruned_path)

    if stats is None:
        stats = Stats.load(filename=pruned_path)

    print('--- TOP ---')
    print_top(stats, k=20)

def main():
    bblfsh_monkey_patch()
    postprocess(sys.argv[1])
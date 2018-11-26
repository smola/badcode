
import collections
import math
import os.path
import sys
import typing

from .stats import *
from .bblfshutil import *
from .bblfshutil import UAST
from .ranker import Ranker
from .treedist import single_node_merge_precalc
from .treedist import TreeToSeq

import bblfsh

def score1(stats: Stats, key: UAST) -> float:
    s = stats.totals[key]
    if s['added'] > s['deleted']:
        return 0.0

    if 'merged' in s:
        if s['merged_positive'] >= s['merged_negative']:
            return 0.0

    total = float(s['added']+s['deleted'])
    return math.log(total+1) * s['deleted'] / total

def score2(stats: Stats, key: UAST) -> float:
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

def score_avg(stats: Stats, key: UAST) -> float:
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
    for n, uast in enumerate(top):
        print('--- SNIPPET %d ---' % n)
        print('STATS: %s' % stats.totals[uast])
        print('REPOS: %d' % len([1 for d in stats.per_repo.values() if uast in d]))
        print('TEXT:')
        print(stats.text[uast])
        print('UAST:')
        print(uast_pretty_format(uast))
        print()

def merge_same_text(stats: Stats) -> None:
    #FIXME: does not merge per_repo
    per_text = {}
    for uast, st in stats.totals.items():
        text = stats.text[uast]
        if text not in per_text:
            per_text[text] = (uast, st)
        else:
            if len(uast) > len(per_text[text][0]):
                per_text[text] = (uast, st)
    stats.totals = dict(per_text.values())

def merge_similar(stats: Stats) -> None:
    merged_uasts = {}
    merged_sizes = {}
    uasts = []
    positive_uasts = []
    tts = TreeToSeq()
    for uast, sstats in stats.totals.items():
        if len(uast.children) == 0:
            continue
        tree_seq = tts.tree_to_seq(uast)
        if sstats['added'] >= sstats['deleted']:
            positive_uasts.append((uast, sstats, tree_seq))
        else:
            uasts.append((uast, sstats, tree_seq))
    tts = None
    total = len(uasts)
    proc = 0
    for i, (uast, sstats, tree_seq) in enumerate(uasts):
        if proc % 1000 == 0:
            print('Processed: %d/%d)' % (proc, total))
        proc += 1
        for ouast, osstats, otree_seq in uasts[i+1:]:
            merged_uast = single_node_merge_precalc(uast, ouast, tree_seq, otree_seq)
            if merged_uast is None:
                continue
            lst = merged_uasts.get(merged_uast, set([]))
            lst.add(uast)
            lst.add(ouast)
            merged_uasts[merged_uast] = lst
            merged_sizes[merged_uast] = len(tree_seq)

    for merged_uast, lst in merged_uasts.items():
        for ouast in lst:
            stats.merge_uast(dst=merged_uast, src=ouast, positive=False)
        for ouast, sstats, tree_seq in positive_uasts:
            if len(merged_uast) != len(ouast):
                continue
            if uast.match(ouast):
                stats.merge_uast(dst=merged_uast, src=ouast, positive=True)

def postprocess(args):
    path = args.stats

    merged_path = path + '_merged'
    ranked_path = merged_path + '_ranked'
    pruned_path = ranked_path + '_pruned'

    stats = None
    print('--- LOADING STATS ---')

    if not os.path.exists(merged_path):
        if stats is None:
            stats = Stats.load(filename=path)
        #TODO(smola): needed?
        print('--- POSTPROCESSING (merge same text) ---')
        merge_same_text(stats)
        print('--- POSTPROCESSING (merge with wildcards) ---')
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
        min_score = 0.8
        print('--- PRUNING ---')
        print('MIN_SCORE: %f' % min_score)
        print('BEFORE: %d' % len(stats.totals))
        prune(stats, min_score=min_score)
        print('AFTER: %d' % len(stats.totals))
        stats.save(filename=pruned_path)

    if stats is None:
        stats = Stats.load(filename=pruned_path)

    print('--- TOP ---')
    print_top(stats, k=50)

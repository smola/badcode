
import collections
import math
import os.path
import sys
import typing

from .stats import *
from .settings import *
from .bblfshutil import *
from .bblfshutil import UAST
from .ranker import Ranker
from .treedist import single_node_merge_precalc
from .treedist import TreeToSeq

import bblfsh


def score1(stats: Stats, key: UAST) -> float:
    s = stats.totals[key]
    total_repos = len(stats.per_repo)
    score = 0.0
    for d in stats.per_repo.values():
        if key not in d:
            continue
        s = d[key]
        total = s['deleted'] + s['added']
        diff = s['deleted'] - s['added']
        score += math.log(1+total) * diff / total
    return score / total_repos

def score_avg(stats: Stats, key: UAST) -> float:
    s = stats.totals[key]
    scores = [v for k, v in s.items() if k.startswith('score_')]
    return float(sum(scores)) / len(scores)

def compute_ranking(stats: Stats) -> None:
    for uast in stats.totals:
        s = stats.totals[uast]
        s['score_1'] = score1(stats, uast)

    r = Ranker(lambda x: score_avg(stats, x))
    for s in stats.totals:
        r.add(s)
    r.finalize()
    for uast in stats.totals:
        s = stats.totals[uast]
        s['score'] = r.get(uast)

def prune(stats: Stats, min_score: float) -> None:
    stats.totals = dict([(k, v) for k, v in stats.totals.items() if v['score'] >= min_score])
    for d in stats.per_repo.values():
        for snpt in list(d.keys()):
            if snpt not in stats.totals:
                del d[snpt]

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
    uasts = []
    tts = TreeToSeq()
    for uast, sstats in stats.totals.items():
        if len(uast.children) == 0:
            continue
        tree_seq = tts.tree_to_seq(uast)
        uasts.append((uast, tree_seq, sstats))
    tts = None
    total = len(uasts)
    proc = 0
    positive_uasts = {}
    negative_uasts = {}
    for i, (uast, tree_seq, sstats) in enumerate(uasts):
        if proc % 1000 == 0:
            logger.info('Processed: %d/%d)' % (proc, total))
        proc += 1
        for ouast, otree_seq, osstats in uasts[i+1:]:
            merged_uast = single_node_merge_precalc(uast, ouast, tree_seq, otree_seq)
            if merged_uast is None:
                continue
            if sstats['added'] >= sstats['deleted']:
                s = positive_uasts.get(merged_uast, set([]))
                s.add(uast)
                positive_uasts[merged_uast] = s
            else:
                s = negative_uasts.get(merged_uast, set([]))
                s.add(uast)
                negative_uasts[merged_uast] = s
            if osstats['added'] >= osstats['deleted']:
                s = positive_uasts.get(merged_uast, set([]))
                s.add(ouast)
                positive_uasts[merged_uast] = s
            else:
                s = negative_uasts.get(merged_uast, set([]))
                s.add(ouast)
                negative_uasts[merged_uast] = s
    for merged_uast, uast_set in negative_uasts.items():
        uast_set = uast_set & negative_uasts.get(merged_uast, set([]))
        for uast in uast_set:
            stats.merge_uast(dst=merged_uast, src=uast)

def postprocess(args):
    path = args.stats

    merged_path = path + '_merged'
    ranked_path = merged_path + '_ranked'
    pruned_path = ranked_path + '_pruned'

    stats = None

    if not os.path.exists(merged_path):
        if stats is None:
            logger.info('Loading stats: %s' % path)
            stats = Stats.load(filename=path)
        logger.info('Merging same text')
        merge_same_text(stats)
        logger.info('Merging similar trees with wildcards')
        merge_similar(stats)
        logger.info('Saving stats (merged): %s' % merged_path)
        stats.save(filename=merged_path)
    
    if not os.path.exists(ranked_path):
        if stats is None:
            logger.info('Loading stats (merged): %s' % merged_path)
            stats = Stats.load(filename=merged_path)
        logger.info('Ranking')
        compute_ranking(stats)
        logger.info('Saving stats (ranked): %s' % ranked_path)
        stats.save(filename=ranked_path)

    if not os.path.exists(pruned_path):
        if stats is None:
            logger.info('Loading stats (ranked): %s' % ranked_path)
            stats = Stats.load(filename=ranked_path)
        min_score = 0.8
        logger.info('Pruning (min_score=%f)' % min_score)
        logger.info('Before pruning: %d' % len(stats.totals))
        prune(stats, min_score=min_score)
        logger.info('After pruning: %d' % len(stats.totals))
        logger.info('Saving stats (pruned): %s' % pruned_path)
        stats.save(filename=pruned_path)


import math

from .stats import Stats
from .settings import *
from .postprocess import per_repo_score1

def print_top(stats: Stats, k: int) -> None:
    top = list(reversed(sorted(stats.totals.keys(), key=lambda x: stats.totals[x]['score'])))
    top = top[:k]
    print('TOTAL: %d' % len(stats.totals))
    for n, uast in enumerate(top):
        print('--- SNIPPET %d ---' % n)
        print('STATS: %s' % stats.totals[uast])
        print('REPOS: %d' % len([1 for d in stats.per_repo.values() if uast in d]))
        for repo in stats.per_repo.keys():
            score = per_repo_score1(stats, uast, repo)
            if math.isclose(score, 0.0, rel_tol=1e-5):
                continue
            print('REPO SCORE: %s -> %f' % (repo, score))
        print('TEXT:')
        print(stats.text[uast])
        print('UAST:')
        print(str(uast))
        print()

def inspect(args):
    path = args.stats

    merged_path = path + '_merged'
    ranked_path = merged_path + '_ranked'
    pruned_path = ranked_path + '_pruned'

    stats = Stats.load(filename=pruned_path)
    print('--- TOP ---')
    print_top(stats, k=50)


from .stats import Stats
from .settings import *


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

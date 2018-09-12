
import sys

import bblfsh

from badcode.stats import Stats

def analyze(files):
    all_stats = Stats()
    for file in files:
        s = Stats.load(file)
        for n, d in s.data.items():
            if n in all_stats.data:
                all_stats.data[n]['added'] += d['added']
                all_stats.data[n]['deleted'] += d['deleted']
                all_stats.data[n]['repos'] += 1
            else:
                all_stats.data[n] = dict(d)
                all_stats.data[n]['repos'] = 1
    all_stats.save()
    top = list(reversed(sorted(all_stats.data.items(), key=lambda x: x[1]['repos']*1000 + x[1]['deleted'] / float(x[1]['added']+1))))[:50]
    for n, d in top:
        print('---- RESULT ----')
        print('STATS: %s' % d)
        bn = bblfsh.Node()
        bn.ParseFromString(n)
        print('Node: %s' % bn)

def main():
    analyze(sys.argv[1:])

if __name__ == '__main__':
    main()

import math
import sys

from badcode.stats import Stats
from badcode.git import *
from badcode.bblfsh import *

import bblfsh

DEFAULT_MAX_SUBTREE_DEPTH = 4

def evaluate(path):
    bblfsh_monkey_patch()
    stats = Stats.load()
    top = [x[0] for x in list(reversed(sorted(stats.data.items(), key=lambda x: math.log(x[1]['added']+1) * x[1]['added'] / float(x[1]['deleted']+1))))[:100]]
    client = bblfsh.BblfshClient("0.0.0.0:9432")
    repo = open_repository(path)
    head = get_reference(repo, 'refs/heads/master')
    seen = set([])
    for commit in walk_history(repo, head.id):
        for change in extract_changes(commit):
            old_blob = repo.get(change.old_blob_hash)
            try:
                old_response = client.parse(filename=change.old_path, contents=old_blob.data)
            except:
                continue
            if old_response.status != 0:
                logging.error('bblfsh parsing error: %s' % {'file': change.old_path, 'hash': old_blob.id, 'error': str(old_response.errors)})
                continue
            filter_node(old_response.uast)
            subtrees = [subtree for subtree in extract_subtrees(old_response.uast, max_depth=DEFAULT_MAX_SUBTREE_DEPTH, lines=change.deleted_lines)]
            for subtree in subtrees:
                #logging.debug('got subtree')
                if not is_relevant_tree(subtree, change.deleted_lines):
                    #logging.debug('skip non-relevant subtree')
                    continue
                if subtree.internal_type == 'Position':
                    continue
                start, end = get_start_end_lines(subtree)
                #print('START END %d %d' % (start, end))
                n = bblfsh.Node()
                n.ParseFromString(subtree.SerializeToString())
                remove_positions(n)
                ser = n.SerializeToString()
                if n.SerializeToString() in top and ser not in seen:
                    seen.add(ser)
                    print('--- FOUND SNIPPET ---')
                    print('COMMIT %s' % commit.id)
                    print('BLOB %s' % change.old_blob_hash)
                    #old_blob = repo.get(change.old_blob_hash)
                    #print(old_blob.data)
                    snippet = old_blob.data.decode().split('\n')[start-1:end]
                    snippet = '\n'.join(snippet)
                    print(snippet)

def main():
    evaluate(sys.argv[1])
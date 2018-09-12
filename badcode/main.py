
import logging
import sys

import bblfsh

from .bblfsh import *
from .git import *
from .stats import *

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DEFAULT_MAX_SUBTREE_DEPTH = 4

def main():
    bblfsh_monkey_patch()
    stats = Stats()
    client = bblfsh.BblfshClient("0.0.0.0:9432")
    repo = open_repository(sys.argv[1])
    head = get_reference(repo, 'refs/heads/master')
    print(type(head))
    for commit in walk_history(repo, head.id):
        for change in extract_changes(commit):
            logging.debug('processing change: %s' % change)
            old_blob = repo.get(change.old_blob_hash)
            try:
                old_response = client.parse(filename=change.old_path, contents=old_blob.data)
            except:
                continue
            if old_response.status != 0:
                logging.error('bblfsh parsing error: %s' % {'file': change.old_path, 'hash': old_blob.id, 'error': str(old_response.errors)})
                continue
            logging.debug('got bblfsh response')
            filter_node(old_response.uast)
            subtrees = [subtree for subtree in extract_subtrees(old_response.uast, max_depth=DEFAULT_MAX_SUBTREE_DEPTH, lines=change.deleted_lines)]
            for subtree in subtrees:
                #logging.debug('got subtree')
                if not is_relevant_tree(subtree, change.deleted_lines):
                    #logging.debug('skip non-relevant subtree')
                    continue
                if subtree.internal_type == 'Position':
                    continue
                logging.debug('got relevant subtree')
                remove_positions(subtree)
                stats.deleted(subtree)
            new_blob = repo.get(change.new_blob_hash)
            try:
                new_response = client.parse(filename=change.old_path, contents=new_blob.data)
            except:
                continue
            if new_response.status != 0:
                logging.error('bblfsh parsing error: %s' % {'file': change.new_path, 'hash': new_blob.id, 'error': str(new_response.errors)})
                continue
            logging.debug('got bblfsh response')
            filter_node(new_response.uast)
            subtrees = [subtree for subtree in extract_subtrees(new_response.uast, max_depth=DEFAULT_MAX_SUBTREE_DEPTH, lines=change.added_lines)]
            for subtree in subtrees:
                #logging.debug('got subtree')
                if not is_relevant_tree(subtree, change.added_lines):
                    #logging.debug('skip non-relevant subtree')
                    continue
                if subtree.internal_type == 'Position':
                    continue
                logging.debug('got relevant subtree')
                remove_positions(subtree)
                stats.added(subtree)
    stats.save()

if __name__ == '__main__':
    main()
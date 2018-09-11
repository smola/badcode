
import logging
import sys

import bblfsh

from .bblfsh import *
from .git import *

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DEFAULT_MAX_SUBTREE_DEPTH = 4

def main():
    client = bblfsh.BblfshClient("0.0.0.0:9432")
    repo = open_repository(sys.argv[1])
    head = get_reference(repo, 'refs/heads/master')
    print(type(head))
    for commit in walk_history(repo, head.id):
        for change in extract_changes(commit):
            logging.debug('processing change: %s' % change)
            blob = repo.get(change.old_blob_hash)
            response = client.parse(filename=change.old_path, contents=blob.data)
            if response.status != 0:
                logging.error('bblfsh parsing error: %s' % {'file': change.old_path, 'hash': blob.id, 'error': str(response.errors)})
                continue
            logging.debug('got bblfsh response')
            for subtree in extract_subtrees(response.uast, max_depth=DEFAULT_MAX_SUBTREE_DEPTH, lines=change.deleted_lines):
                logging.debug('got subtree')

if __name__ == '__main__':
    main()

import logging

from pygit2 import Repository
from pygit2 import GIT_SORT_TOPOLOGICAL, GIT_SORT_REVERSE

logger = logging.getLogger(__name__)

def is_vendor(path):
    return path.startswith('vendor')

def get_language(path):
    if path.endswith('.go'):
        return 'Go'
    return 'Other'

def extract_changes(path: str, ref: str, languages=['Go']):
    repo = Repository(path)
    ref = repo.lookup_reference(ref)
    commit = ref.peel()
    for commit in repo.walk(repo.head.target, GIT_SORT_TOPOLOGICAL | GIT_SORT_REVERSE):
        if len(commit.parents) == 0:
            logging.debug('skip commit with no parents', extra={'commit': commit.id})
            continue
        if len(commit.parents) > 2:
            logging.debug('skip merge commit', extra={'commit': commit.id})
            continue
        parent = commit.parents[0]
        diff = commit.tree.diff_to_tree(
            parent.tree,
            context_lines=0,
            interhunk_lines=1)
        diff.find_similar()
        for patch in diff:
            if patch.delta.status_char() != 'M':
                continue
            old_path = patch.delta.old_file.path
            new_path = patch.delta.new_file.path
            if is_vendor(old_path):
                continue
            if is_vendor(new_path):
                continue
            if get_language(new_path) not in languages:
                continue
            lines = []
            for hunk in patch.hunks:
                lines += [line.old_lineno for line in hunk.lines if line.new_lineno == -1]
            yield '%s -> %s %s' % (old_path, new_path, ','.join(map(str, lines)))

if __name__ == '__main__':
    import sys
    deltad = None
    for ch in extract_changes(sys.argv[1], 'refs/heads/master'):
        deltad = ch
        print(ch)
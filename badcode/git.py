
import logging
import typing

import pygit2

logger = logging.getLogger(__name__)

class Change:
    def __init__(self,
        old_path: str, old_blob_hash: str,
        deleted_lines: typing.Iterable[int],
        new_path: str, new_blob_hash: str,
        added_lines: typing.Iterable[int]) -> None:
        self._old_path = old_path
        self._old_blob_hash = old_blob_hash
        self._deleted_lines = set(deleted_lines)
        self._new_path = new_path
        self._new_blob_hash = new_blob_hash
        self._added_lines = added_lines

    @property
    def old_path(self) -> str:
        return self._old_path
    
    @property
    def old_blob_hash(self) -> str:
        return self._old_blob_hash

    @property
    def deleted_lines(self) -> typing.Set[int]:
        return self._deleted_lines

    @property
    def new_path(self) -> str:
        return self._new_path
    
    @property
    def new_blob_hash(self) -> str:
        return self._new_blob_hash

    @property
    def added_lines(self) -> typing.Set[int]:
        return self._added_lines

    def __repr__(self) -> str:
        return 'Change(old_path=%s, old_blob_hash=%s, lines=%s)' % (self.old_path, self.old_blob_hash, ','.join(map(str, self.deleted_lines)))

def is_vendor(path):
    return path.startswith('vendor')

def get_language(path: str) -> str:
    if path.endswith('.go'):
        return 'Go'
    return 'Other'

def open_repository(path: str) -> pygit2.Repository:
    return pygit2.Repository(path)

def get_reference(repo: pygit2.Repository, ref: str) -> pygit2.Commit:
    refobj = repo.lookup_reference(ref)
    commit = refobj.peel()
    return commit

def walk_history(repo: pygit2.Repository, commit_id: pygit2.Oid) -> typing.Generator[pygit2.Commit,None,None]:
    for c in repo.walk(commit_id, pygit2.GIT_SORT_TOPOLOGICAL|pygit2.GIT_SORT_REVERSE):
        yield c

def extract_changes(commit: pygit2.Commit, languages=['Go']) -> typing.Generator[Change,None,None]:
    if len(commit.parents) == 0:
        logging.debug('skip commit with no parents: %s' % {'commit': commit.id})
        return
    if len(commit.parents) > 2:
        logging.debug('skip merge commit: %s' % {'commit': commit.id})
        return
    parent = commit.parents[0]
    diff = commit.tree.diff_to_tree(
        parent.tree,
        context_lines=0,
        interhunk_lines=1)
    diff.find_similar()
    for patch in diff:
        if patch.delta.status_char() != 'M':
            continue
        old_blob_hash = patch.delta.old_file.id
        new_blob_hash = patch.delta.new_file.id
        old_path = patch.delta.old_file.path
        new_path = patch.delta.new_file.path
        if is_vendor(old_path):
            continue
        if is_vendor(new_path):
            continue
        if get_language(new_path) not in languages:
            continue
        deleted_lines: typing.List[int] = []
        for hunk in patch.hunks:
            deleted_lines += [line.old_lineno for line in hunk.lines if line.new_lineno == -1]
        added_lines: typing.List[int] = []
        for hunk in patch.hunks:
            added_lines += [line.new_lineno for line in hunk.lines if line.old_lineno == -1]
        yield Change(old_path=old_path,
            old_blob_hash=old_blob_hash,
            deleted_lines=deleted_lines,
            new_path=new_path,
            new_blob_hash=new_blob_hash,
            added_lines=added_lines)

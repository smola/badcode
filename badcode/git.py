
import logging
import types
import typing

import pygit2

logger = logging.getLogger(__name__)

def git_apply_settings():
    pygit2.settings.cache_object_limit(pygit2.GIT_OBJ_BLOB, 100 * 1024 * 1024)
    pygit2.settings.cache_object_limit(pygit2.GIT_OBJ_COMMIT, 100 * 1024 * 1024)
    pygit2.settings.cache_object_limit(pygit2.GIT_OBJ_TREE, 100 * 1024 * 1024)
    pygit2.settings.cache_object_limit(pygit2.GIT_OBJ_TAG, 100 * 1024 * 1024)
    

class FileFilter:
    def match(self, path: str, size: int ) -> bool:
        return True

class LanguageFilter(FileFilter):
    def __init__(self, languages: typing.Iterable[str]) -> None:
        self.languages = set([l.lower() for l in languages])

    def match(self, path: str, size: int) -> bool:
        language = get_language(path).lower()
        return language in self.languages

class VendorFilter(FileFilter):
    def __init__(self):
        pass

    def match(self, path: str, size: int) -> bool:
        return not is_vendor(path)

class MaxSizeFilter(FileFilter):
    def __init__(self, max_size: int) -> None:
        self.max_size = max_size

    def match(self, path: str, size: int) -> bool:
        return size <= self.max_size

class Change:
    def __init__(self,
        commit_id: pygit2.Oid,
        old_path: str, old_blob_hash: str,
        deleted_lines: typing.Iterable[int],
        new_path: str, new_blob_hash: str,
        added_lines: typing.Iterable[int]) -> None:
        self._commit_id = commit_id
        self._old_path = old_path
        self._old_blob_hash = old_blob_hash
        self._deleted_lines = set(deleted_lines)
        self._new_path = new_path
        self._new_blob_hash = new_blob_hash
        self._added_lines = set(added_lines)

    @property
    def commit_id(self):
        return self._commit_id

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
        return 'Change(commit_id=%s, old_path=%s, old_blob_hash=%s, lines=%s)' % (
            self.commit_id, self.old_path, self.old_blob_hash,
            ','.join(map(str, self.deleted_lines)))

def is_vendor(path):
    if path.startswith('vendor'):
        return True
    if 'bindata.go' in path:
        return True
    if path.endswith('.pb.go'):
        return True
    return False

def get_language(path: str) -> str:
    if path.endswith('.go'):
        return 'Go'
    return 'Other'


class Repository:
    def __init__(self, repo: typing.Union[str,pygit2.Repository]) -> None:
        if isinstance(repo, str):
            repo = pygit2.Repository(repo)
        self.repo = repo

    def reference(self, ref: str) -> pygit2.Commit:
        refobj = self.repo.lookup_reference(ref)
        commit = refobj.peel()
        return commit

    def get(self, id: pygit2.Oid) -> pygit2.Object:
        return self.repo.get(id)

    def walk_history(self,
            commit: typing.Union[pygit2.Oid,pygit2.Commit]) -> typing.Generator[pygit2.Commit,None,None]:
        if isinstance(commit, pygit2.Commit):
            commit_id = commit.id
        else:
            commit_id = commit
        for c in self.repo.walk(commit_id, pygit2.GIT_SORT_TOPOLOGICAL|pygit2.GIT_SORT_REVERSE):
            yield c

    def extract_changes(self,
            commits: typing.Union[pygit2.Commit,typing.Generator[pygit2.Commit,None,None]],
            filters: typing.Iterable[FileFilter]) -> typing.Generator[pygit2.Commit,None,None]:
        if isinstance(commits, types.GeneratorType):
            for commit in commits:
                for change in self.extract_changes(commit, filters):
                    yield change
            return
        
        commit = commits
        logger.debug('extracting changes from commit: %s' % commit.id)
        if len(commit.parents) == 0:
            logging.debug('skip commit with no parents: %s' % {'commit': commit.id})
            return
        if len(commit.parents) > 2:
            logging.debug('skip merge commit: %s' % {'commit': commit.id})
            return
        parent = commit.parents[0]
        diff = parent.tree.diff_to_tree(
            commit.tree,
            context_lines=0,
            interhunk_lines=1)
        #PERF: diff.find_similar()
        for patch in diff:
            change = self.extract_change_from_patch(commit.id, patch, filters)
            if change is None:
                continue
            yield change

    def extract_change_from_patch(self,
            commit_id: pygit2.Oid,
            patch: pygit2.Patch,
            filters: typing.Iterable[FileFilter]) -> typing.Optional[Change]:
        if patch.delta.status_char() != 'M':
            return None
        old_blob_hash = patch.delta.old_file.id
        new_blob_hash = patch.delta.new_file.id
        old_path = patch.delta.old_file.path
        new_path = patch.delta.new_file.path
        old_size = patch.delta.old_file.size
        new_size = patch.delta.new_file.size

        for filter in filters:
            if not filter.match(path=old_path, size=old_size):
                logger.debug('filtered out old path: %s (%s)' % (old_path, filter))
                return None
            if not filter.match(path=new_path, size=new_size):
                logger.debug('filtered out new path: %s (%s)' % (new_path, filter))
                return None

        logger.debug('extracting changes from file: %s -> %s' % (old_path, new_path))

        deleted_lines: typing.List[int] = []
        for hunk in patch.hunks:
            deleted_lines += [line.old_lineno for line in hunk.lines if line.new_lineno == -1]
        added_lines: typing.List[int] = []
        for hunk in patch.hunks:
            added_lines += [line.new_lineno for line in hunk.lines if line.old_lineno == -1]
        return Change(
            commit_id=commit_id,
            old_path=old_path,
            old_blob_hash=old_blob_hash,
            deleted_lines=deleted_lines,
            new_path=new_path,
            new_blob_hash=new_blob_hash,
            added_lines=added_lines)

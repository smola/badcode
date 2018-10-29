
import logging
import types
import typing

from cachetools import LRUCache
import bblfsh
import pygit2

from .bblfshutil import filter_node
from .core import Change
from .core import File
from .extract import TreeExtractor
from .settings import *
from .stats import Stats

logger = logging.getLogger(__name__)

def _git_apply_settings():
    pygit2.settings.cache_object_limit(pygit2.GIT_OBJ_BLOB, 100 * 1024 * 1024)
    pygit2.settings.cache_object_limit(pygit2.GIT_OBJ_COMMIT, 100 * 1024 * 1024)
    pygit2.settings.cache_object_limit(pygit2.GIT_OBJ_TREE, 100 * 1024 * 1024)
    pygit2.settings.cache_object_limit(pygit2.GIT_OBJ_TAG, 100 * 1024 * 1024)

_git_apply_settings()

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

def is_vendor(path):
    if path.startswith('vendor') or '/vendor/' in path:
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

def get_repository(repo_name: str) -> pygit2.Repository:
    repo_dir = DEFAULT_REPO_DIR / repo_name
    if repo_dir.exists():
        return pygit2.Repository(str(repo_dir))
    logger.info('cloning repository: %s' % repo_name)
    url = 'git://github.com/%s.git' % repo_name
    repo = pygit2.clone_repository(
        url=url,
        path=str(repo_dir),
        bare=True)
    return repo

class GitRepository:
    def __init__(self,
            repo: typing.Union[str,pygit2.Repository],
            client: bblfsh.BblfshClient,
            filters: typing.Iterable[FileFilter]) -> None:
        if isinstance(repo, str):
            repo = pygit2.Repository(repo)
        self.repo = repo
        self.client = client
        self.filters = filters
        #TODO(smola): parameterize cache size
        self.cache = LRUCache(maxsize=2000)

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

    def extract_changes_from_history(self,
            commit: typing.Union[pygit2.Oid,pygit2.Commit]) -> typing.Generator[pygit2.Commit,None,None]:
        for c in self.extract_changes(self.walk_history(commit)):
            yield c

    def extract_changes(self,
            commits: typing.Union[pygit2.Commit,typing.Generator[pygit2.Commit,None,None]],
            ) -> typing.Generator[pygit2.Commit,None,None]:
        if isinstance(commits, types.GeneratorType):
            for commit in commits:
                for change in self.extract_changes(commit):
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
            change = self._extract_change_from_patch(commit.id, patch)
            if change is None:
                continue
            yield change

    def _extract_change_from_patch(self,
            commit_id: pygit2.Oid,
            patch: pygit2.Patch) -> typing.Optional[Change]:
        if patch.delta.status_char() != 'M':
            return None
        if not self._match_patch(patch):
            return None

        logger.debug('extracting changes from file: %s -> %s' % (
            patch.delta.old_file.path, patch.delta.new_file.path))

        added_lines, deleted_lines = self._get_added_deleted_lines(patch)
        base_file = self._extract_file_from_difffile(patch.delta.old_file)
        if not base_file:
            return None
        head_file = self._extract_file_from_difffile(patch.delta.new_file)
        if not head_file:
            return None

        return Change(
            commit_id=str(commit_id),
            base=base_file,
            head=head_file,
            deleted_lines=deleted_lines,
            added_lines=added_lines)

    def _match_patch(self, patch: pygit2.Patch) -> bool:
        for filter in self.filters:
            if not filter.match(
                    path=patch.delta.old_file.path,
                    size=patch.delta.old_file.size):
                logger.debug('filtered out old path: %s (%s)' % (patch.delta.old_file.path, filter))
                return False
            if not filter.match(
                    path=patch.delta.new_file.path,
                    size=patch.delta.new_file.size):
                logger.debug('filtered out new path: %s (%s)' % (patch.delta.new_file.path, filter))
                return False
        return True

    def _get_added_deleted_lines(self, patch: pygit2.Patch) -> typing.Tuple[typing.List[int],typing.List[int]]:
        deleted_lines: typing.List[int] = []
        added_lines: typing.List[int] = []
        for hunk in patch.hunks:
            deleted_lines += [line.old_lineno for line in hunk.lines if line.new_lineno == -1]
            added_lines += [line.new_lineno for line in hunk.lines if line.old_lineno == -1]
        return added_lines, deleted_lines

    def _extract_file_from_difffile(self, file: pygit2.DiffFile) -> File:
        blob_hash = str(file.id)
        content, uast = self._get_blob_uast(blob_hash, file.path)
        if not uast:
            return None
        return File(
            blob_hash=blob_hash,
            path=file.path,
            content=content,
            uast=uast
        )

    def _get_blob_uast(self, blob_hash, path):
        if blob_hash in self.cache:
            content, uast = self.cache[blob_hash]
            return content, uast
        content = self.repo.get(blob_hash).data
        uast = self._get_uast(path, blob_hash, content)
        self.cache[blob_hash] = (content, uast)
        return content, uast

    def _get_uast(self, path, blob_hash, content):
        try:
            response = self.client.parse(filename=path, contents=content)
        except Exception as exc:
            logging.error('bblfsh parsing error raised: %s' % {
                'file': path,
                'hash': blob_hash,
                'exception': exc})
            return None
        if response.status != 0:
                logging.error('bblfsh parsing error: %s' % {
                    'file': path,
                    'hash': blob_hash,
                    'error': str(response.errors)})
                return None
        uast = response.uast
        #TODO(smola): remove this, do it later in Stats
        filter_node(uast)
        return uast

class GitRepositoryTrainer(GitRepository):

    def __init__(self,
            repo_name: str,
            repo: typing.Union[str,pygit2.Repository],
            client: bblfsh.BblfshClient,
            stats: Stats,
            filters: typing.Iterable[FileFilter]) -> None:
        super(GitRepositoryTrainer, self).__init__(repo, client, filters)
        self.repo_name = repo_name
        self.stats = stats
        self.tree_extractor = TreeExtractor(
            min_depth=DEFAULT_MIN_SUBTREE_DEPTH,
            max_depth=DEFAULT_MAX_SUBTREE_DEPTH,
            min_size=DEFAULT_MIN_SUBTREE_SIZE,
            max_size=DEFAULT_MAX_SUBTREE_SIZE
        )

    def train_all(self) -> None:
        head = self.reference('refs/heads/master')
        if head is None:
            logger.warning('no master')
            return
        for change in self.extract_changes_from_history(head):
            self.train(change)

    def train(self, change: Change) -> None:
        logger.debug('processing change: %s' % change)
        for snippet in self.tree_extractor.get_snippets(
                file=change.base,
                lines=change.deleted_lines):
            self.stats.deleted(self.repo_name, snippet)
        for snippet in self.tree_extractor.get_snippets(
                file=change.head,
                lines=change.added_lines):
            self.stats.added(self.repo_name, snippet)

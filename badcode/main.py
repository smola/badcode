
import logging
import multiprocessing
import pathlib
import sys

import bblfsh
from cachetools import LRUCache

from .bblfsh import *
from .git import *
from .stats import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_MIN_SUBTREE_DEPTH = 2
DEFAULT_MAX_SUBTREE_DEPTH = 4
DEFAULT_MIN_SUBTREE_SIZE = 2
DEFAULT_MAX_SUBTREE_SIZE = 20
DEFAULT_DATA_DIR = pathlib.Path('data')
DEFAULT_REPO_DIR = DEFAULT_DATA_DIR / 'repos'
DEFAULT_STATS_DIR = DEFAULT_DATA_DIR / 'stats'

#XXX: To avoid bblfsh downscaling, we set workers to CPUs+1
DEFAULT_WORKERS = multiprocessing.cpu_count() + 1


class RepositoryAnalyzer:
    def __init__(self,
            client: bblfsh.BblfshClient,
            stats: Stats,
            repo_name: str,
            repo: Repository) -> None:
        self.cache = LRUCache(maxsize=2000)
        self.repo_name = repo_name
        self.repo = repo
        self.client = client
        self.stats = stats

    def get_snippets(self,
            path: str,
            blob_id: pygit2.Oid,
            lines: typing.Set[int]) -> typing.Generator[bblfsh.Node,None,None]:
        if blob_id in self.cache:
            blob, uast = self.cache[blob_id]
        else:
            blob = self.repo.get(blob_id)
            try:
                response = self.client.parse(filename=path, contents=blob.data)
            except Exception as exc:
                logging.error('bblfsh parsing error raised: %s' % {
                    'file': path,
                    'hash': blob.id,
                    'exception': exc})
                return
            if response.status != 0:
                logging.error('bblfsh parsing error: %s' % {
                    'file': path,
                    'hash': blob.id,
                    'error': str(response.errors)})
                return
            uast = response.uast
            filter_node(uast)
            self.cache[blob_id] = (blob, uast)
        subtrees = [subtree for subtree in extract_subtrees(uast,
            min_depth=DEFAULT_MIN_SUBTREE_DEPTH,
            max_depth=DEFAULT_MAX_SUBTREE_DEPTH,
            min_size=DEFAULT_MIN_SUBTREE_SIZE,
            max_size=DEFAULT_MAX_SUBTREE_SIZE,
            lines=lines)]
        n = 0
        for subtree in subtrees:
            if not is_relevant_tree(subtree, lines):
                return
            if subtree.internal_type == 'Position':
                return
            n += 1
            ser = subtree.SerializeToString()
            subtree = bblfsh.Node()
            subtree.ParseFromString(ser)
            snippet = Snippet.from_uast_blob(subtree, blob.data.decode())
            remove_positions(snippet.uast)

            yield snippet
        logging.debug('got relevant subtrees: %d', n)

    def process_change(self,
            change: Change) -> None:
        logging.debug('processing change: %s' % change)
        for snippet in self.get_snippets(
                path=change.old_path,
                blob_id=change.old_blob_hash,
                lines=change.deleted_lines):
            self.stats.deleted(self.repo_name, snippet)
        for snippet in self.get_snippets(
                path=change.new_path,
                blob_id=change.new_blob_hash,
                lines=change.added_lines):
            self.stats.added(self.repo_name, snippet)

    def analyze(self):
        logger.info('analyzing repository: %s' % self.repo_name)
        head = self.repo.reference('refs/heads/master')
        if head is None:
            logger.info('no master')
            return
        history = self.repo.walk_history(head)
        changes = self.repo.extract_changes(
            commits=history,
            filters=[VendorFilter(), LanguageFilter(['Go'])])
        for change in changes:
            self.process_change(change)

def get_repository(repo_name: str) -> pygit2.Repository:
    repo_dir = DEFAULT_REPO_DIR / repo_name
    if repo_dir.exists():
        return Repository(str(repo_dir))
    logger.info('cloning repository: %s' % repo_name)
    url = 'git://github.com/%s.git' % repo_name
    repo = pygit2.clone_repository(
        url=url,
        path=str(repo_dir),
        bare=True)
    return Repository(repo)

def main_per_repository(repo_name: str) -> None:
    STATS_PATH = DEFAULT_STATS_DIR / repo_name / 'stats.db'
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if STATS_PATH.exists():
        logger.info('Stats already exist for %s' % repo_name)
        return

    stats = Stats()
    client = bblfsh.BblfshClient("0.0.0.0:9432")
    repo = get_repository(repo_name)
    analyzer = RepositoryAnalyzer(
        repo=repo,
        repo_name=repo_name,
        client=client,
        stats=stats)
    analyzer.analyze()
    logger.info('saving stats: %s' % STATS_PATH)
    analyzer.stats.save(filename=STATS_PATH)
    logger.info('saved stats: %s' % STATS_PATH)

def main():
    repo_list_path = sys.argv[1]
    git_apply_settings()
    bblfsh_monkey_patch()
    DEFAULT_REPO_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_STATS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info('Reading repository list from %s' % repo_list_path)
    with open(repo_list_path, 'r') as f:
        repo_list = f.read().splitlines()
    logger.info('Start repository analysis with %d workers' % DEFAULT_WORKERS)
    with multiprocessing.Pool(processes=DEFAULT_WORKERS) as pool:
        pool.map(main_per_repository, repo_list)
    logger.info('Finished repository analysis')

    logger.info('Merge stats')
    global_stats = Stats()
    for repo_name in repo_list:
        local_stats = Stats.load(DEFAULT_STATS_DIR / repo_name / 'stats.db')
        global_stats += local_stats
    logger.info('Saving merged stats')
    global_stats.save(DEFAULT_DATA_DIR / 'stats.db')
    logger.info('Saved merged stats')

if __name__ == '__main__':
    main()

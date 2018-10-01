
import pathlib
import logging
import queue
import sys
import threading

import bblfsh
from cachetools import LRUCache

from .bblfsh import *
from .git import *
from .stats import *

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DEFAULT_MAX_SUBTREE_DEPTH = 4
DEFAULT_MAX_SUBTREE_SIZE = 20
DEFAULT_DATA_DIR = pathlib.Path('data')
DEFAULT_REPO_DIR = DEFAULT_DATA_DIR / 'repos'


class RepositoryAnalyzer:
    def __init__(self,
            client: bblfsh.BblfshClient,
            stats: Stats,
            repo_name: str,
            repo: Repository) -> None:
        self.cache = LRUCache(maxsize=200)
        self.repo_name = repo_name
        self.repo = repo
        self.client = client
        self.stats = stats
        self.queue: queue.Queue = None

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
            logging.debug('got bblfsh response')
            uast = response.uast
            filter_node(uast)
            self.cache[blob_id] = (blob, uast)
        subtrees = [subtree for subtree in extract_subtrees(uast,
            max_depth=DEFAULT_MAX_SUBTREE_DEPTH,
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

    def _process_changes_worker(self) -> None:
        while True:
            change: typing.Optional[Change] = self.queue.get()
            if change is None:
                return
            try:
                self.process_change(change)
            except Exception as exc:
                logger.errror('exception in thread: %s' % exc)
            self.queue.task_done()

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
        self.queue = queue.Queue(maxsize=200)
        threads = []
        for i in range(8):
            t = threading.Thread(target=self._process_changes_worker)
            t.start()
            threads.append(t)
        for change in changes:
            self.queue.put(change)
        logger.debug('joining queue')
        self.queue.join()
        logger.debug('stopping threads')
        for i in range(len(threads)):
            self.queue.put(None)
        logger.debug('joining threads')
        for t in threads:
            t.join()
        self.stats.save()

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

def main():
    bblfsh_monkey_patch()
    stats = Stats.load_or_create()
    client = bblfsh.BblfshClient("0.0.0.0:9432")
    with open(sys.argv[1], 'r') as f:
        repo_list = f.read().splitlines()
    DEFAULT_REPO_DIR.mkdir(parents=True, exist_ok=True)
    for repo_name in repo_list:
        repo = get_repository(repo_name)
        analyzer = RepositoryAnalyzer(
            repo=repo,
            repo_name=repo_name,
            client=client,
            stats=stats)
        analyzer.analyze()


if __name__ == '__main__':
    main()
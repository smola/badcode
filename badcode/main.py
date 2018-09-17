
import pathlib
import logging
import sys

import bblfsh

from .bblfsh import *
from .git import *
from .stats import *

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DEFAULT_MAX_SUBTREE_DEPTH = 4
DEFAULT_DATA_DIR = pathlib.Path('data')
DEFAULT_REPO_DIR = DEFAULT_DATA_DIR / 'repos'

def get_snippets(
            repo: Repository,
            client: bblfsh.BblfshClient,
            path: str,
            blob_id: pygit2.Oid,
            lines: typing.Set[int]) -> typing.Generator[bblfsh.Node,None,None]:
        blob = repo.get(blob_id)
        try:
            response = client.parse(filename=path, contents=blob.data)
        except:
            logging.error('bblfsh parsing error raised: %s' % {
                'file': path,
                'hash': blob.id,
                'error': str(response.errors)})
            return
        if response.status != 0:
            logging.error('bblfsh parsing error: %s' % {
                'file': path,
                'hash': blob.id,
                'error': str(response.errors)})
            return
        logging.debug('got bblfsh response')
        filter_node(response.uast)
        subtrees = [subtree for subtree in extract_subtrees(response.uast, max_depth=DEFAULT_MAX_SUBTREE_DEPTH, lines=lines)]
        for subtree in subtrees:
            if not is_relevant_tree(subtree, lines):
                return
            if subtree.internal_type == 'Position':
                return
            logging.debug('got relevant subtree')
            ser = subtree.SerializeToString()
            subtree = bblfsh.Node()
            subtree.ParseFromString(ser)
            snippet = Snippet.from_uast_blob(subtree, blob.data.decode())
            remove_positions(snippet.uast)

            yield snippet

def analyze_repository(
        client: bblfsh.BblfshClient,
        stats: Stats,
        repo_name: str):

    repo = get_repository(repo_name)
    logger.info('analyzing repository: %s' % repo_name)
    head = repo.reference('refs/heads/master')
    if head is None:
        logger.info('no master')
        return
    history = repo.walk_history(head)
    changes = repo.extract_changes(
        commits=history,
        filters=[VendorFilter(), LanguageFilter(['Go'])])
    for change in changes:
        logging.debug('processing change: %s' % change)
        for snippet in get_snippets(
                repo=repo,
                client=client,
                path=change.old_path,
                blob_id=change.old_blob_hash,
                lines=change.deleted_lines):
            stats.deleted(repo_name, snippet)
        for snippet in get_snippets(
                repo=repo,
                client=client,
                path=change.new_path,
                blob_id=change.new_blob_hash,
                lines=change.added_lines):
            stats.added(repo_name, snippet)
    stats.save()

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
        analyze_repository(
            client=client,
            stats=stats,
            repo_name=repo_name)

if __name__ == '__main__':
    main()
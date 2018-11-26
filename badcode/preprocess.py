
import multiprocessing
import sys

import bblfsh
from cachetools import LRUCache

from .extract import TreeExtractor
from .git import *
from .settings import *
from .stats import *

def main_per_repository(repo_name: str) -> None:
    STATS_PATH = DEFAULT_STATS_DIR / repo_name / 'stats.db'
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if STATS_PATH.exists():
        logger.info('Stats already exist for %s' % repo_name)
        return

    stats = Stats()
    client = bblfsh.BblfshClient("0.0.0.0:9432")
    repo = get_repository(repo_name)
    trainer = GitRepositoryTrainer(
        repo=repo,
        repo_name=repo_name,
        client=client,
        stats=stats,
        filters=[
            VendorFilter(),
            LanguageFilter(['Go']),
            MaxSizeFilter(max_size=10*1024)]
    )
    trainer.train_all()
    logger.info('saving stats: %s' % STATS_PATH)
    stats.save(filename=STATS_PATH)
    logger.info('saved stats: %s' % STATS_PATH)

def preprocess(args):
    repo_list_path = args.repositories
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
    global_stats.save(DEFAULT_STATS_PATH)
    logger.info('Saved merged stats')


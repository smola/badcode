
import logging
import multiprocessing
import pathlib

DEFAULT_MIN_SUBTREE_DEPTH = 2
DEFAULT_MAX_SUBTREE_DEPTH = 4
DEFAULT_MIN_SUBTREE_SIZE = 2
DEFAULT_MAX_SUBTREE_SIZE = 20

DEFAULT_DATA_DIR = pathlib.Path('data')
DEFAULT_REPO_DIR = DEFAULT_DATA_DIR / 'repos'
DEFAULT_STATS_DIR = DEFAULT_DATA_DIR / 'stats'

DEFAULT_STATS_PATH = DEFAULT_DATA_DIR / 'stats.db'

#XXX: To avoid bblfsh downscaling, we set workers to CPUs+1
DEFAULT_WORKERS = multiprocessing.cpu_count() + 1

DEFAULT_BBLFSHD = '0.0.0.0:9432'

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
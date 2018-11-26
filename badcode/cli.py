
import argparse
import os

from .analyzer import serve
from .postprocess import postprocess
from .preprocess import preprocess
from .inspect import inspect
from .settings import *

def main():
    parser = argparse.ArgumentParser(description='badcode')
    subparsers = parser.add_subparsers(help='sub-command help')
    
    analyzer_parser = subparsers.add_parser('analyzer', help='run analyzer')
    analyzer_parser.add_argument('--host', type=str, default=os.environ.get('BADCODE_HOST', '0.0.0.0'))
    analyzer_parser.add_argument('--port', type=int, default=int(os.environ.get('BADCODE_PORT', 2022)))
    analyzer_parser.add_argument('--data-service', type=str, default=os.environ.get('BADCODE_DATA_SERVICE_URL', 'localhost:10301'))
    analyzer_parser.add_argument('--model', type=str, default=os.environ.get('BADCODE_MODEL', str(DEFAULT_STATS_PATH) + '_merged_ranked_pruned'))
    analyzer_parser.set_defaults(func=serve)

    def train(args):
        preprocess(args)
        postprocess(args)

    train_parser = subparsers.add_parser('train', help='train with repositories')
    train_parser.add_argument('--stats', type=str, default=str(DEFAULT_STATS_PATH))
    train_parser.add_argument('repositories', type=str)
    train_parser.set_defaults(func=train)

    inspect_parser = subparsers.add_parser('inspect', help='inspect model')
    inspect_parser.add_argument('--stats', type=str, default=str(DEFAULT_STATS_PATH))
    inspect_parser.set_defaults(func=inspect)
 
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()

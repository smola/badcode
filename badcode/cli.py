
import argparse
import os

from .analyzer import serve
from .postprocess import postprocess
from .preprocess import preprocess
from .settings import *

def main():
    parser = argparse.ArgumentParser(description='badcode')
    subparsers = parser.add_subparsers(help='sub-command help')
    
    analyzer_parser = subparsers.add_parser('analyzer', help='run analyzer')
    analyzer_parser.add_argument('--host', type=str, default=os.environ.get('BADCODE_HOST', "0.0.0.0"))
    analyzer_parser.add_argument('--port', type=int, default=int(os.environ.get('BADCODE_PORT', 2022)))
    analyzer_parser.add_argument('--data-service', type=str, default=os.environ.get('BADCODE_DATA_SERVICE_URL', "localhost:10301"))
    analyzer_parser.set_defaults(func=serve)

    preprocess_parser = subparsers.add_parser('preprocess', help='preprocess repositories')
    preprocess_parser.add_argument('repositories', type=str)
    preprocess_parser.set_defaults(func=preprocess)

    postprocess_parser = subparsers.add_parser('postprocess', help='postprocess stats')
    postprocess_parser.add_argument('--stats', type=str, default=str(DEFAULT_STATS_PATH))
    postprocess_parser.set_defaults(func=postprocess)


    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()

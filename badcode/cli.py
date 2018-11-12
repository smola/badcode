
import argparse

from .postprocess import postprocess
from .preprocess import preprocess
from .settings import *

def main():
    parser = argparse.ArgumentParser(description='badcode')
    subparsers = parser.add_subparsers(help='sub-command help')
    
    preprocess_parser = subparsers.add_parser('preprocess', help='preprocess repositories')
    preprocess_parser.add_argument('repositories', type=argparse.FileType('r', encoding='UTF-8'))
    preprocess_parser.set_defaults(func=preprocess)

    postprocess_parser = subparsers.add_parser('postprocess', help='postprocess stats')
    postprocess_parser.add_argument('--stats', type=str, default=str(DEFAULT_STATS_PATH))
    postprocess_parser.set_defaults(func=postprocess)


    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()

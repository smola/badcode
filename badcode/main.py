
import sys

from .git import *

def main():
    repo = open_repository(sys.argv[1])
    head = get_reference(repo, 'refs/heads/master')
    print(type(head))
    for commit in walk_history(repo, head.id):
        for ch in extract_changes(commit):
            print(ch)

if __name__ == '__main__':
    main()
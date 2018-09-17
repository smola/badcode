
import math
import sys
import typing

from badcode.stats import Stats
from badcode.git import *
from badcode.bblfsh import *
from badcode.main import *

import bblfsh

def score(s: typing.Dict[str,int]):
    return s['deleted'] / float(s['added']+s['deleted'])

def evaluate(path: str):
    bblfsh_monkey_patch()
    stats = Stats.load()
    top = [x[0] for x in reversed(sorted(stats.totals.items(), key=lambda x: score(x[1])))]
    top = top[:100]
    client = bblfsh.BblfshClient("0.0.0.0:9432")
    repo = Repository(path)
    head = repo.reference('refs/heads/master')
    history = repo.walk_history(head)
    seen: typing.Set[Snippet] = set([])
    changes = repo.extract_changes(
        commits=history,
        filters=[VendorFilter(), LanguageFilter(['Go'])])
    for change in changes:
        snippets = get_snippets(
            repo=repo,
            client=client,
            path=change.new_path,
            blob_id=change.new_blob_hash,
            lines=change.added_lines)
        for snippet in snippets:
            if snippet in seen:
                continue
            if snippet not in top:
                continue
            seen.add(snippet)
            print('--- FOUND SNIPPET ---')
            print(snippet.text)

def main():
    evaluate(sys.argv[1])
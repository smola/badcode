
import typing

import bblfsh

def extract_subtrees(uast: bblfsh.Node, max_depth: int, lines: typing.Iterable[int]) -> typing.Generator[bblfsh.Node,None,None]:
    if not isinstance(lines, set):
        lines = set(lines)

    yield uast

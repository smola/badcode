
import logging
import typing
from typing import Generator, Iterable, List, Set, Tuple

import bblfsh
import pygit2

from .core import File
from .bblfshutil import UAST


class Path:
    def __init__(self,
            path: List['Path'],
            node: bblfsh.Node,
            lines: Set[int]) -> None:
        self.path = path
        self.node = node
        self.is_relevant = is_relevant_node(node, lines=lines)
        self._is_relevant_tree = None
        self._children = None
        self._lines = lines
        self._depth = None
        self._size = None

    @property
    def children(self):
        if self._children is None:
            self._children = [Path(
                path=self.path + [self],
                node=c,
                lines=self._lines) for c in self.node.children]
        return self._children

    @property
    def depth(self):
        if self._depth is None:
            if len(self.children) == 0:
                self._depth = 1
            else:
                self._depth = max([c.depth for c in self.children])+1
        return self._depth

    @property
    def size(self):
        if self._size is None:
            if len(self.children) == 0:
                self._size = 1
            else:
                self._size = sum([c.size for c in self.children])+1
        return self._size

    @property
    def is_relevant_tree(self):
        if self._is_relevant_tree is None:
            self._is_relevant_tree = self.__is_relevant_tree()
        return self._is_relevant_tree

    def __is_relevant_tree(self):
        if self.is_relevant:
            return True
        for c in self.children:
            if c.is_relevant_tree:
                return True
        return False


def is_relevant_tree(uast: bblfsh.Node, lines: Set[int]) -> bool:
    if is_relevant_node(uast, lines):
        return True
    for child in uast.children:
        if is_relevant_tree(child, lines):
            return True
    return False

def is_relevant_node(uast: bblfsh.Node, lines: Set[int]) -> bool:
    if uast.start_position.line in lines:
        return True
    if uast.end_position.line in lines:
        return True
    if uast.start_position.line >= 1 and uast.end_position.line >= 1:
        for line in lines:
            if line >= uast.start_position.line and line <= uast.end_position.line:
                return True
    return False

def extract_paths(root: bblfsh.Node, lines: Set[int]) -> Generator[Path,None,None]:
    queue = [Path(path=[], node=root, lines=lines)]
    while len(queue) > 0:
        path = queue.pop()
        if len(path.children) == 0:
            yield path
            continue
        queue.extend(path.children)

def extract_subtrees(
        uast: bblfsh.Node,
        min_depth: int,
        max_depth: int,
        min_size: int,
        max_size: int,
        lines: Iterable[int]) -> Generator[bblfsh.Node,None,None]:
    if not isinstance(lines, set):
        lines = set(lines)

    already_extracted: typing.Set[int] = set([])

    paths = extract_paths(uast, lines=lines)
    for path in paths:
        if path.size > max_size:
            continue
        is_relevant = path.is_relevant
        if is_relevant and path.size >= min_size and path.depth >= min_depth:
            yield path.node
        if max_depth == 1:
            continue
        for depth in range(2, max_depth+1):
            if len(path.path) < depth-1:
                break
            parent = path.path[-1*(depth - 1)]
            if parent.depth > max_depth:
                break
            if parent.size > max_size:
                break
            if parent.size < min_size:
                continue
            if parent.depth < min_depth:
                continue
            is_relevant |= parent.is_relevant
            if is_relevant:
                i = id(parent.node)
                if i in already_extracted:
                    continue
                already_extracted.add(i)
                yield parent.node

def uast_blob_to_snippet(
            uast: bblfsh.Node,
            blob: str) -> str:
    start, end = _get_start_end_lines(uast)
    lines = blob.split('\n')
    lines = [l for n, l in enumerate(lines) if n + 1 >= start and n + 1 <= end]
    text = '\n'.join(lines)
    return text

def _get_start_end_lines(uast: bblfsh.Node) -> typing.Tuple[int, int]:
    start = uast.start_position.line
    end = uast.end_position.line
    for child in uast.children:
        cstart, cend = _get_start_end_lines(child)
        if start == 0 or cstart < start:
            start = cstart
        if end == 0 or cend > end:
            end = cend
    return start, end

def first_line(uast: bblfsh.Node) -> int:
    max_line = 9223372036854775807
    line = max_line
    if uast.start_position.line != 0:
        line = uast.start_position.line
    children = [c for c in uast.children]
    if len(children) > 0:
        min_child = min([first_line(child) for child in uast.children])
        line = min([line, min_child])
    if line == max_line:
        line = 0
    return line

class TreeExtractor:

    def __init__(self,
            min_depth: int,
            max_depth: int,
            min_size: int,
            max_size: int
            ) -> None:
        self.min_depth = min_depth
        self.max_depth = max_depth
        self.min_size = min_size
        self.max_size = max_size

    def get_snippets(self,
            file: File,
            lines: Set[int]) -> Generator[Tuple[int,UAST,str],None,None]:
        subtrees = [(first_line(u), u) for u in extract_subtrees(
            uast=file.uast,
            min_depth=self.min_depth,
            max_depth=self.max_depth,
            min_size=self.min_size,
            max_size=self.max_size,
            lines=lines)]
        n = 0
        for line, subtree in subtrees:
            if not is_relevant_tree(subtree, lines):
                return
            if subtree.internal_type == 'Position':
                return
            n += 1
            snippet = uast_blob_to_snippet(subtree, file.content.decode())
            subtree = UAST.from_bblfsh(subtree)
            yield line, subtree, snippet
        logging.debug('got relevant subtrees: %d', n)

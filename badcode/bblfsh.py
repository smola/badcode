
import typing

import bblfsh

class Snippet:
    def __init__(self,
            uast: bblfsh.Node,
            text: str) -> None:
        self._ser = None
        self._uast = uast
        self._text = text

    @staticmethod
    def from_uast_blob(
            uast: bblfsh.Node,
            blob: str) -> 'Snippet':
        start, end = get_start_end_lines(uast)
        lines = blob.split('\n')
        lines = [l for n, l in enumerate(lines) if n + 1 >= start and n + 1 <= end]
        text = '\n'.join(lines)
        return Snippet(uast, text)

    @property
    def uast(self):
        self._ensure_unser()
        return self._uast
    
    @property
    def text(self):
        return self._text

    def _ensure_ser(self):
        if self._ser is None:
            self._ser = self._uast.SerializeToString()

    def _ensure_unser(self):
        if self._uast is None:
            self._uast = bblfsh.Node()
            self._uast.ParseFromString(self._ser)

    def __hash__(self) -> int:
        return hash(self._text)

    def __eq__(self, other) -> bool:
        return self._text == other._text

    def __getstate__(self):
        self._ensure_ser()
        state = dict(self.__dict__)
        del state['_uast']
        return state

class Node:
    def __init__(self, lines: typing.Set[int]=set([])) -> None:
        self.lines = lines


def extract_node(node: bblfsh.Node) -> Node:
    return Node(lines=set(range(node.start_position.line, node.end_position.line + 1)))
        

def extract_leaves(uast: bblfsh.Node, lines: typing.Set[int]) -> typing.Tuple[typing.List[bblfsh.Node], typing.Dict[int, bblfsh.Node]]:
    leaves = []
    parents = {}
    root = extract_node(uast)
    queue = [(root, uast)]
    while queue:
        parent, parent_uast = queue.pop()
        
        # building the parents map
        for child in parent_uast.children:
            parents[id(child)] = parent_uast
            
        # traversing the uast bfs with line filtering
        children_nodes = [extract_node(child) for child in parent_uast.children]
        if set(parent.lines) & set(lines):
            queue.extend(zip(children_nodes, parent_uast.children))
            if not parent_uast.children:
                leaves.append(parent_uast)
    return leaves, parents

# for testing, same function as above but without line filtering
def extract_leaves_without_lines(uast: bblfsh.Node) -> typing.Tuple[typing.List[bblfsh.Node], typing.Dict[int, bblfsh.Node]]:
    leaves = []
    parents = {}
    queue = [uast]
    while queue:
        parent_uast = queue.pop()
        
        # building the parents map
        for child in parent_uast.children:
            parents[id(child)] = parent_uast
            
        # traversing the uast bfs with line filtering
        children_nodes = [child for child in parent_uast.children]
        queue.extend(children_nodes)
        if not parent_uast.children:
            leaves.append(parent_uast)
    return leaves, parents

def extract_subtrees(uast: bblfsh.Node, max_depth: int, lines: typing.Iterable[int]) -> typing.Generator[bblfsh.Node,None,None]:
    if not isinstance(lines, set):
        lines = set(lines)

    already_extracted: typing.Set[int] = set([])
    leaves, parents = extract_leaves(uast, lines)
    for leaf in leaves:
        depth = 1
        node = leaf
        while depth < max_depth and id(node) in parents:
            parent = parents[id(node)]
            node = parent
            depth += 1
        if id(node) not in already_extracted:
            already_extracted.add(id(node))
            yield node

def bblfsh_monkey_patch() -> None:
    bblfsh.Node.__hash__ = uast_hash
    bblfsh.Node.__eq__ = uast_eq

def uast_hash(a: bblfsh.Node) -> int:
    return hash(tuple(uast_types(a, 2)))
    
def uast_types(a: bblfsh.Node, depth: int) -> typing.List[str]:
    lst = [a.internal_type]
    if depth == 0:
        return lst
    for child in a.children:
        lst += uast_types(a, depth-1)
    return lst

def uast_eq(a: bblfsh.Node, b: bblfsh.Node) -> bool:
    if a.internal_type != b.internal_type:
        return False
    if a.token != b.token:
        return False
    if len(a.children) != len(b.children):
        return False
    for ac, bc in zip(a.children, b.children):
        if not uast_eq(ac, bc):
            return False
    return True        

def is_relevant_tree(uast: bblfsh.Node, lines: typing.Set[int]) -> bool:
    if uast.start_position.line in lines:
        return True
    if uast.end_position.line in lines:
        return True
    if uast.start_position.line >= 1 and uast.end_position.line >= 1:
        for line in lines:
            if line >= uast.start_position.line and line <= uast.end_position.line:
                return True
    for child in uast.children:
        if is_relevant_tree(child, lines):
            return True
    return False

def get_start_end_lines(uast: bblfsh.Node) -> typing.Tuple[int, int]:
    start = uast.start_position.line
    end = uast.end_position.line
    for child in uast.children:
        cstart, cend = get_start_end_lines(child)
        if start == 0 or cstart < start:
            start = cstart
        if end == 0 or cend > end:
            end = cend
    return start, end

def filter_node(uast: bblfsh.Node) -> None:
    while len(uast.roles) > 0:
        uast.roles.pop()
    uast.properties.clear()
    for child in list(uast.children):
        if child.internal_type == 'Position':
            uast.children.remove(child)
            continue
        filter_node(child)

def remove_positions(uast: bblfsh.Node) -> None:
    set_zero_position(uast)
    for child in uast.children:
        remove_positions(child)

def set_zero_position(uast: bblfsh.Node) -> None:
    uast.start_position.offset = 0
    uast.start_position.line = 0
    uast.start_position.col = 0
    uast.end_position.offset = 0
    uast.end_position.line = 0
    uast.end_position.col = 0

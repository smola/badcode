
import typing

import bblfsh


class Node:
    def __init__(self, lines: typing.List[int]=None):
        self.lines = lines


def extract_node(node: bblfsh.Node) -> Node:
    return Node(lines=range(node.start_position.line, node.end_position.line + 1))
        

def extract_leaves(uast: bblfsh.Node, lines: typing.List[int]) -> typing.Tuple[typing.List[bblfsh.Node], typing.Dict[int, bblfsh.Node]]:
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
        if set.intersection(set(parent.lines), lines):
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

    already_extracted = set()
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
    if uast.start_position.line > 1 and uast.end_position.line > 1:
        for line in lines:
            if line > uast.start_position.line and line < uast.end_position.line:
                return True
    for child in uast.children:
        if is_relevant_tree(child, lines):
            return True
    return False

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

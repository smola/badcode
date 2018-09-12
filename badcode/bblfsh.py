
import typing

import bblfsh


class Node:
    def __init__(self, lines: typing.List[int]=None):
        self.lines = lines


def extract_node(node: bblfsh.Node) -> Node:
    return Node(lines=range(node.start_position.line, node.end_position.line + 1))
        

def extract_leaves(uast: bblfsh.Node, lines: typing.List[int]) -> typing.Tuple[typing.List[bblfsh.Node], typing.Dict[bblfsh.Node]]:
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


def extract_subtrees(uast: bblfsh.Node, max_depth: int, lines: typing.Iterable[int]) -> typing.Generator[bblfsh.Node,None,None]:
    if not isinstance(lines, set):
        lines = set(lines)

    leaves, parents = extract_leaves(uast, lines)
    for leaf in leaves:
        depth = 1
        node = leaf
        while depth < depth and id(node) in parents:
            parent = parents[id(node)]
            node = parent
            depth += 1
        yield node

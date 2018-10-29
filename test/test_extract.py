
import unittest

from bblfsh import Node
from badcode.extract import extract_subtrees
from badcode.extract import extract_paths
from badcode.extract import is_relevant_node

def test_is_relevant_node():
    node = Node()
    node.start_position.line = 1
    node.end_position.line = 1

    assert is_relevant_node(node, lines=set([1]))
    assert is_relevant_node(node, lines=set([1,2]))
    assert is_relevant_node(node, lines=set([1,3]))
    assert not is_relevant_node(node, lines=set([2]))
    assert not is_relevant_node(node, lines=set([2,3]))
    
    node.start_position.line = 2
    node.end_position.line = 4
    assert is_relevant_node(node, lines=set([2]))
    assert is_relevant_node(node, lines=set([4]))
    assert is_relevant_node(node, lines=set([3]))
    assert not is_relevant_node(node, lines=set([1,5]))

def test_extract_subtrees_all_positions():
    root = Node()
    root.internal_type = 'root'
    root.start_position.line = 1
    root.end_position.line = 4

    child1 = Node()
    child1.internal_type = '1'
    child1.start_position.line = 1
    child1.end_position.line = 1

    child2 = Node()
    child2.internal_type = '2'
    child2.start_position.line = 2
    child2.end_position.line = 3
    child2a = Node()
    child2a.internal_type = '2a'
    child2a.start_position.line = 2
    child2a.end_position.line = 2
    child2b = Node()
    child2b.internal_type = '2b'
    child2b.start_position.line = 3
    child2b.end_position.line = 3

    child3 = Node()
    child3.internal_type = '3'
    child3.start_position.line = 4
    child3.end_position.line = 4

    child2.children.extend([child2a, child2b])
    root.children.extend([child1, child2, child3])

    paths = [p for p in extract_paths(root, lines=set([1]))]
    assert 4 == len(paths)

    subtrees = [s for s in extract_subtrees(root,
        min_depth=1, max_depth=1, min_size=1, max_size=100, lines=set([3]))]
    assert [child2b] == subtrees

    subtrees = [s for s in extract_subtrees(root,
        min_depth=1, max_depth=1, min_size=1, max_size=100, lines=set([4]))]
    assert [child3] == subtrees

    subtrees = [s for s in extract_subtrees(root,
        min_depth=1, max_depth=2, min_size=1, max_size=100, lines=set([3]))]
    assert 2 == len(subtrees)
    assert child2b in subtrees
    assert child2 in subtrees

    subtrees = [s for s in extract_subtrees(root,
        min_depth=1, max_depth=100, min_size=1, max_size=3, lines=set([3]))]
    assert 2 == len(subtrees)
    assert child2b in subtrees
    assert child2 in subtrees

    subtrees = [s for s in extract_subtrees(root,
        min_depth=1, max_depth=100, min_size=1, max_size=2, lines=set([3]))]
    assert 1 == len(subtrees)
    assert child2b in subtrees

    deeper_root1 = Node()
    deeper_root2 = Node()
    deeper_root3 = Node()
    deeper_root3.children.extend([root])
    deeper_root2.children.extend([deeper_root3])
    deeper_root1.children.extend([deeper_root2])
    subtrees = [s for s in extract_subtrees(deeper_root1,
        min_depth=1, max_depth=2, min_size=1, max_size=100, lines=set([3]))]
    assert 2 == len(subtrees)
    assert child2b in subtrees
    assert child2 in subtrees



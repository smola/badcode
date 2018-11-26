
import unittest

from badcode.tree import Tree

def test_tree_eq_hash():
    a: Tree[int] = Tree(key=1)
    b: Tree[int] = Tree(key=1)
    c: Tree[int] = Tree(key=2)
    assert a == b
    assert hash(a) == hash(b)
    assert a != c
    assert hash(a) != hash(c)

    a = a.with_children(children=(Tree(key=2),))
    b = b.with_children(children=(Tree(key=2),))
    c = c.with_children(children=(Tree(key=2),))
    assert a == b
    assert hash(a) == hash(b)
    assert a != c
    assert hash(a) != hash(c)

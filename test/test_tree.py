
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

def test_tree_eq_none():
    assert Tree(key=1) != None

def test_tree_len():
    t = Tree(key=1)
    assert len(t) == 1

    t = Tree(key=1, children=[
        Tree(key=2)
    ])
    assert len(t) == 2

    t = Tree(key=1, children=[
        Tree(key=2),
        Tree(key=3, children=[
            Tree(key=4),
        ]),
    ])
    assert len(t) == 4

def test_repr():
    t = Tree(key=1)
    assert t.__repr__() == 'Tree(key=1)'

    t = Tree(key=1, children=[
        Tree(key=2),
        Tree(key=3)
    ])
    assert t.__repr__() == 'Tree(key=1, children=(Tree(key=2), Tree(key=3)))'

def test_state():
    t = Tree(key=1, children=[
        Tree(key=2),
        Tree(key=3)
    ])

    state = t.__getstate__()
    assert list(state.keys()) == ['key', 'children']

    t2 = Tree(key=0)
    t2.__setstate__(state)
    assert t == t2
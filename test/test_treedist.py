
import unittest

from bblfsh import Node
from badcode.treedist import node_distance
from badcode.treedist import node_merge

import zss

def test_node_distance():
    a = Node()
    a.internal_type = 'A'
    a.token = 'a'
    b = Node()
    b.internal_type = 'B'
    b.token = 'b'
    
    assert (2, [('update', ('A', 'a'), ('B', 'b'))]) == node_distance(a, b)
    assert (0, [('match', ('A', 'a'), ('A', 'a'))]) == node_distance(a, a)

    a = Node()
    a.internal_type = 'A'
    a.token = 'a'
    b = Node()
    b.internal_type = 'A'
    b.token = 'b'
    
    assert (1, [('update', ('A', 'a'), ('A', 'b'))]) == node_distance(a, b)

    a = Node()
    a.internal_type = 'A'
    a.token = 'a'
    a1 = Node()
    a1.internal_type = 'A1'
    a1.token = 'a1'
    a.children.extend([a1])
    b = Node()
    b.internal_type = 'A'
    b.token = 'b'
    
    assert (101, [('remove', ('A1', 'a1'), None), ('update', ('A', 'a'), ('A', 'b'))]) == node_distance(a, b)

    a = Node()
    a.internal_type = 'A'
    a.token = 'a'
    a1 = Node()
    a1.internal_type = 'A1'
    a1.token = 'a1'
    a2 = Node()
    a2.internal_type = 'A2'
    a2.token = 'a2'
    a21 = Node()
    a21.internal_type = 'A21'
    a21.token = 'a21'
    a2.children.extend([a21])
    a.children.extend([a1, a2])

    b = Node()
    b.internal_type = 'A'
    b.token = 'a'
    a1 = Node()
    a1.internal_type = 'A1'
    a1.token = 'a1'
    a2 = Node()
    a2.internal_type = 'A2'
    a2.token = 'a2'
    a21 = Node()
    a21.internal_type = 'B21'
    a21.token = 'b21'
    a2.children.extend([a21])
    b.children.extend([a1, a2])

    assert (2, [
        ('match', ('A1', 'a1'), ('A1', 'a1')),
        ('update', ('A21', 'a21'), ('B21', 'b21')),
        ('match', ('A2', 'a2'), ('A2', 'a2')),
        ('match', ('A', 'a'), ('A', 'a')),
        ]) == node_distance(a, b)

def test_node_merge():
    a = Node()
    a.internal_type = 'A'
    a.token = 'a'

    b = Node()
    b.internal_type = 'B'
    b.token = 'b'
    
    c = Node()
    c.internal_type = 'MATCH_ANY'
    c.token = 'MATCH_ANY'

    assert a == node_merge(a, a)
    assert node_merge(a, b) is None
    assert c == node_merge(a, b, max_dist=2)

    b = Node()
    b.internal_type = 'A'
    b.token = 'b'
    
    c = Node()
    c.internal_type = 'A'
    c.token = 'MATCH_ANY'
    assert c == node_merge(a, b, max_dist=1)

    a = Node()
    a.internal_type = 'A'
    a.token = 'a'
    a1 = Node()
    a1.internal_type = 'A1'
    a1.token = 'a1'
    a2 = Node()
    a2.internal_type = 'A2'
    a2.token = 'a2'
    a21 = Node()
    a21.internal_type = 'A21'
    a21.token = 'a21'
    a2.children.extend([a21])
    a.children.extend([a1, a2])

    b = Node()
    b.internal_type = 'A'
    b.token = 'a'
    a1 = Node()
    a1.internal_type = 'A1'
    a1.token = 'a1'
    a2 = Node()
    a2.internal_type = 'A2'
    a2.token = 'a2'
    a21 = Node()
    a21.internal_type = 'B21'
    a21.token = 'b21'
    a2.children.extend([a21])
    b.children.extend([a1, a2])

    c = Node()
    c.internal_type = 'A'
    c.token = 'a'
    a1 = Node()
    a1.internal_type = 'A1'
    a1.token = 'a1'
    a2 = Node()
    a2.internal_type = 'A2'
    a2.token = 'a2'
    a21 = Node()
    a21.internal_type = 'MATCH_ANY'
    a21.token = 'MATCH_ANY'
    a2.children.extend([a21])
    c.children.extend([a1, a2])

    assert c == node_merge(a, b, max_dist=2)

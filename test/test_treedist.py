
import unittest

from bblfsh import Node
from badcode.treedist import single_node_merge
from badcode.treedist import TreeToSeq
from badcode.treedist import single_node_merge_precalc


def test_single_node_merge():
    a = Node()
    a.internal_type = 'A'
    a.token = 'a'

    b = Node()
    b.internal_type = 'B'
    b.token = 'b'
    
    c = Node()
    c.internal_type = 'MATCH_ANY'
    c.token = 'MATCH_ANY'

    assert single_node_merge(a, a) is None
    assert c == single_node_merge(a, b)

    b = Node()
    b.internal_type = 'A'
    b.token = 'b'
    
    c = Node()
    c.internal_type = 'A'
    c.token = 'MATCH_ANY'
    assert c == single_node_merge(a, b)

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

    assert c == single_node_merge(a, b)

def test_single_node_merge_precalc():
    tts = TreeToSeq()

    a = Node()
    a.internal_type = 'A'
    a.token = 'a'
    a_seq = tts.tree_to_seq(a)

    b = Node()
    b.internal_type = 'B'
    b.token = 'b'
    b_seq = tts.tree_to_seq(b)
    
    c = Node()
    c.internal_type = 'MATCH_ANY'
    c.token = 'MATCH_ANY'

    assert single_node_merge_precalc(a, a, a_seq, a_seq) is None
    assert c == single_node_merge_precalc(a, b, a_seq, b_seq)

    b = Node()
    b.internal_type = 'A'
    b.token = 'b'
    b_seq = tts.tree_to_seq(b)

    c = Node()
    c.internal_type = 'A'
    c.token = 'MATCH_ANY'
    assert c == single_node_merge_precalc(a, b, a_seq, b_seq)

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
    a_seq = tts.tree_to_seq(a)

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
    b_seq = tts.tree_to_seq(b)

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

    assert c == single_node_merge_precalc(a, b, a_seq, b_seq)

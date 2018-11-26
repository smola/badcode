
import unittest

from bblfsh import Node

from badcode.bblfshutil import UAST, WILDCARD
from badcode.treedist import single_node_merge
from badcode.treedist import TreeToSeq
from badcode.treedist import single_node_merge_precalc


def test_single_node_merge():
    a = UAST(key=('A', 'a'))
    b = UAST(key=('B', 'b'))
    c = UAST(key=(WILDCARD, WILDCARD))
    assert single_node_merge(a, a) is None
    assert c == single_node_merge(a, b)

    b = UAST(key=('A', 'b'))
    c = UAST(key=('A', WILDCARD))
    assert c == single_node_merge(a, b)

    a = UAST(key=('A', 'a'), children=(
        UAST(key=('A1', 'a1')),
        UAST(key=('A2', 'a2'), children=(
            UAST(key=('A21', 'a21')),
        ))
    ))
    b = UAST(key=('A', 'a'), children=(
        UAST(key=('A1', 'a1')),
        UAST(key=('A2', 'a2'), children=(
            UAST(key=('B21', 'b21')),
        ))
    ))
    c = UAST(key=('A', 'a'), children=(
        UAST(key=('A1', 'a1')),
        UAST(key=('A2', 'a2'), children=(
            UAST(key=(WILDCARD, WILDCARD)),
        ))
    ))
    assert c == single_node_merge(a, b)

def test_single_node_merge_precalc():
    tts = TreeToSeq()

    a = UAST(key=('A', 'a'))
    b = UAST(key=('B', 'b'))
    c = UAST(key=(WILDCARD, WILDCARD))
    a_seq = tts.tree_to_seq(a)
    b_seq = tts.tree_to_seq(b)
    assert single_node_merge_precalc(a, a, a_seq, a_seq) is None
    assert c == single_node_merge_precalc(a, b, a_seq, b_seq)

    b = UAST(key=('A', 'b'))
    c = UAST(key=('A', WILDCARD))
    b_seq = tts.tree_to_seq(b)
    assert c == single_node_merge_precalc(a, b, a_seq, b_seq)

    a = UAST(key=('A', 'a'), children=(
        UAST(key=('A1', 'a1')),
        UAST(key=('A2', 'a2'), children=(
            UAST(key=('A21', 'a21')),
        ))
    ))
    b = UAST(key=('A', 'a'), children=(
        UAST(key=('A1', 'a1')),
        UAST(key=('A2', 'a2'), children=(
            UAST(key=('B21', 'b21')),
        ))
    ))
    c = UAST(key=('A', 'a'), children=(
        UAST(key=('A1', 'a1')),
        UAST(key=('A2', 'a2'), children=(
            UAST(key=(WILDCARD, WILDCARD)),
        ))
    ))
    a_seq = tts.tree_to_seq(a)
    b_seq = tts.tree_to_seq(b)
    assert c == single_node_merge_precalc(a, b, a_seq, b_seq)

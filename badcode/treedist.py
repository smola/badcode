
import itertools
import typing

import bblfsh

from .bblfshutil import uast_eq_node
from .bblfshutil import uast_iter


def fast_distance(a: bblfsh.Node, b: bblfsh.Node, max_dist: int) -> int:
    stack_a = [a]
    stack_b = [b]
    dist = 0
    while len(stack_a) > 0 and len(stack_b):
        cur_a = None
        cur_b = None
        if len(stack_a) > 0:
            cur_a = stack_a.pop()
            stack_a.extend(cur_a.children)
            cur_a = (cur_a.internal_type, cur_a.token)
        if len(stack_b) > 0:
            cur_b = stack_b.pop()
            stack_b.extend(cur_b.children)
            cur_b = (cur_b.internal_type, cur_b.token)
        if cur_a != cur_b:
            dist += 1
        if dist > max_dist:
            return dist
    return dist

def single_node_merge(a: bblfsh.Node, b: bblfsh.Node) -> typing.Optional[bblfsh.Node]:
    """
    Return a node that matches both inputs by using a single wildcard.
    If there is more than one different node, None is returned.
    """

    diff_pos = None
    diff_token = False
    diff_internal_type = False
    n = 0
    for an, bn in itertools.zip_longest(uast_iter(a), uast_iter(b)):
        if an is None or bn is None:
            return None
        if uast_eq_node(an, bn):
            n += 1
            continue
        if diff_pos is not None:
            return None
        diff_pos = n
        diff_internal_type = an.internal_type != bn.internal_type
        diff_token = an.token != bn.token
        n += 1

    if diff_pos is None:
        return None

    ser = a.SerializeToString()
    node = bblfsh.Node()
    node.ParseFromString(ser)

    n = 0
    for an in uast_iter(node):
        if n != diff_pos:
            n += 1
            continue
        if diff_internal_type:
            an.internal_type = 'MATCH_ANY'
        if diff_token:
            an.token = 'MATCH_ANY'
        break

    return node

def single_node_merge_precalc(
        a: bblfsh.Node, b: bblfsh.Node,
        a_tree_seq: typing.List[int],
        b_tree_seq: typing.List[int],
        ) -> typing.Optional[bblfsh.Node]:
    """
    Return a node that matches both inputs by using a single wildcard.
    If there is more than one different node, None is returned.
    """

    if len(a_tree_seq) != len(b_tree_seq):
        return None

    diff_pos = None
    n = 0
    for an, bn in zip(a_tree_seq, b_tree_seq):
        if an == bn:
            n += 1
            continue
        if diff_pos is not None:
            return None
        diff_pos = n
        n += 1

    if diff_pos is None:
        return None

    ser = a.SerializeToString()
    node = bblfsh.Node()
    node.ParseFromString(ser)

    n = 0
    for nn, an, bn in zip(uast_iter(node), uast_iter(a), uast_iter(b)):
        if n != diff_pos:
            n += 1
            continue
        if an.internal_type != bn.internal_type:
            nn.internal_type = 'MATCH_ANY'
        if an.token != bn.token:
            nn.token = 'MATCH_ANY'
        break

    return node

class TreeToSeq:
    def __init__(self):
        self.vocab = {}
    
    def tree_to_seq(self, a: bblfsh.Node) -> typing.List[int]:
        seq: typing.List[int] = []
        for node in uast_iter(a):
            word = '%s/%s' % (node.internal_type, node.token)
            seq_id = self._seq_id(word)
            seq.append(seq_id)
        return seq

    def _seq_id(self, word: str) -> int:
        seq_id = self.vocab.get(word, None)
        if seq_id is None:
            seq_id = len(self.vocab) + 1
            self.vocab[word] = seq_id
        return seq_id


import itertools
from typing import List, Optional, Set, Tuple

from .bblfshutil import UAST
from .bblfshutil import WILDCARD
from .bblfshutil import uast_eq_node


def single_node_merge(a: UAST, b: UAST) -> Optional[UAST]:
    """
    Return a node that matches both inputs by using a single wildcard.
    If there is more than one different node, None is returned.
    """

    diff_pos = None
    diff_token = False
    diff_internal_type = False
    n = 0
    for an, bn in itertools.zip_longest(a, b):
        if an is None or bn is None:
            return None
        if an.key == bn.key:
            n += 1
            continue
        if diff_pos is not None:
            return None
        diff_pos = n
        diff_internal_type = an.key[0] != bn.key[0]
        diff_token = an.key[1] != bn.key[1]
        n += 1

    if diff_pos is None:
        return None

    node = a.__copy__()
    n = 0
    for an in node:
        if n != diff_pos:
            n += 1
            continue
        if diff_internal_type:
            an._key = (WILDCARD, an.key[1])
        if diff_token:
            an._key = (an.key[0], WILDCARD)
        break

    return node

def single_node_merge_precalc(
        a: UAST, b: UAST,
        a_tree_seq: List[int],
        b_tree_seq: List[int],
        ) -> Optional[UAST]:
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

    node = a.__copy__()

    n = 0
    for nn, an, bn in zip(node, a, b):
        if n != diff_pos:
            n += 1
            continue
        if an.key[0] != bn.key[0]:
            nn._key = (WILDCARD, nn.key[1])
        if an.key[1] != bn.key[1]:
            nn._key = (nn.key[0], WILDCARD)
        break

    return node

class TreeToSeq:
    def __init__(self):
        self.vocab = {}
    
    def tree_to_seq(self, a: UAST) -> List[int]:
        seq: List[int] = []
        for node in a:
            seq_id = self._seq_id(node.key)
            seq.append(seq_id)
        return seq

    def _seq_id(self, word: Tuple[str,str]) -> int:
        seq_id = self.vocab.get(word, None)
        if seq_id is None:
            seq_id = len(self.vocab) + 1
            self.vocab[word] = seq_id
        return seq_id

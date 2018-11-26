
import collections
import itertools
import typing
from typing import Iterable, Tuple

import bblfsh

from .tree import Tree

WILDCARD = '_MATCH_ANY_'

class UAST(Tree[Tuple[str,str]]):
    
    def __init__(self, key: Tuple[str,str], children: Iterable['UAST']=tuple()) -> None:
        super(UAST, self).__init__(key, children)

    @staticmethod
    def from_bblfsh(node: bblfsh.Node) -> 'UAST':
        return UAST(
            key=(node.internal_type, node.token),
            children=(uast_to_tree(n) for n in node.children))

    def match(self, other: 'UAST') -> bool:
        return uast_eq_wildcards(self, other)
    
    def __str__(self) -> str:
        return uast_pretty_format(self)

def uast_to_tree(node: bblfsh.Node) -> Tree[Tuple[str, str]]:
    children = (uast_to_tree(n) for n in node.children if n.internal_type != 'Position')
    return Tree(
        key=(node.internal_type, node.token),
        children=children)

def uast_eq_node(a: UAST, b: UAST) -> bool:
    return a.key == b.key

def uast_eq_node_wildcards(a: UAST, b: UAST) -> bool:
    if a.key[0] != b.key[0] and a.key[0] != WILDCARD and b.key[0] != WILDCARD:
        return False
    if a.key[1] != b.key[1] and a.key[1] != WILDCARD and b.key[1] != WILDCARD:
        return False
    return True

def uast_eq(a: UAST, b: UAST, eqf=uast_eq_node) -> bool:
    if b is None:
        return False
    for an, bn in itertools.zip_longest(a, b):
        if an is None or bn is None:
            return False
        if not eqf(an, bn):
            return False
    return True

def uast_eq_wildcards(a: UAST, b: UAST) -> bool:
    return uast_eq(a, b, eqf=uast_eq_node_wildcards)

def uast_pretty_format(n: UAST, indent=0) -> str:
    s = '%stype: %s, token: %s' % ('. ' * indent, n.key[0], n.key[1])
    for c in n.children:
        s += '\n' + uast_pretty_format(c, indent=indent+1)
    return s

def filter_node(uast: bblfsh.Node) -> None:
    """
    Removes any data from the bblfsh.Node that is not used at all.
    """
    while len(uast.roles) > 0:
        uast.roles.pop()
    uast.properties.clear()
    for child in list(uast.children):
        if child.internal_type == 'Position':
            uast.children.remove(child)
            continue
        filter_node(child)

import typing

import bblfsh
import zss

def _get_children(a: bblfsh.Node) -> typing.List[bblfsh.Node]:
    return [c for c in a.children]

def _get_label(a: bblfsh.Node) -> str:
    return '%s/%s' % (a.internal_type, a.token)

def _label_dist(a: str, b: str) -> int:
    if a == b:
        return 0
    return 1

def node_distance(a: bblfsh.Node, b: bblfsh.Node) -> int:
    return zss.simple_distance(a, b,
        get_children=_get_children,
        get_label=_get_label,
        label_dist=_label_dist
    )

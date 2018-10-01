
import typing

import bblfsh
import zss

def _get_children(a: bblfsh.Node) -> typing.List[bblfsh.Node]:
    return [c for c in a.children]

def _get_label(a: bblfsh.Node) -> str:
    return '%s/%s' % (a.internal_type, a.token)

def _label_dist(a: str, b: str) -> int:
    if a == '':
        return 2
    if b == '':
        return 2
    idx = a.index('/')
    a = (a[:idx], a[:idx])
    idx = b.index('/')
    b = (b[:idx], b[:idx])
    if a == b:
        return 0
    if a[0] == b[0]:
        return 1
    return 2

def _update_cost(a: bblfsh.Node, b: bblfsh.Node) -> int:
    if a.internal_type != b.internal_type:
        return 2
    if a.token != b.token:
        return 1
    return 0

def _get_pair_label(node):
    if node is None:
        return None
    return (node.internal_type, node.token)

def _convert_op(op):
    if op.type == zss.Operation.remove:
        opt = 'remove'
    elif op.type == zss.Operation.insert:
        opt = 'insert'
    elif op.type == zss.Operation.update:
        opt = 'update'
    elif op.type == zss.Operation.match:
        opt = 'match'
    else:
        raise Exception('invalid operation type: %d' % op.type)
    return (opt, _get_pair_label(op.arg1), _get_pair_label(op.arg2))

def node_distance(a: bblfsh.Node, b: bblfsh.Node):
    cost, ops = zss.distance(a, b,
        get_children=_get_children,
        insert_cost=lambda node: 100,
        remove_cost=lambda node: 100,
        update_cost=_update_cost,
        return_operations=True,
    )

    return cost, [_convert_op(op) for op in ops]

def node_merge(
        a: bblfsh.Node, b: bblfsh.Node,
        max_dist: int = 1) -> typing.Optional[bblfsh.Node]:
    """
    Return a node that matches both inputs by using wildcards.
    If distance between both trees is greater than the given max_dist,
    None is returned.
    """
    cost, ops = zss.distance(a, b,
        get_children=_get_children,
        insert_cost=lambda node: 100,
        remove_cost=lambda node: 100,
        update_cost=_update_cost,
        return_operations=True,
    )

    if cost > max_dist:
        return None

    ser = a.SerializeToString()
    node = bblfsh.Node()
    node.ParseFromString(ser)

    def match(op, node):
        if op.type == zss.Operation.match:
            return True
        if op.type == zss.Operation.update:
            if node.internal_type != op.arg2.internal_type:
                node.internal_type = 'MATCH_ANY'
            if node.token != op.arg2.token:
                node.token = 'MATCH_ANY'
            return True
        return False

    # Traverse tree in postorder, which is the same order as the
    # edit operations from zss. Add wildcards whenever an update
    # operation is found.
    i = 0
    stack = [node]
    visited = set()
    while len(stack) > 0:
        cur = stack[-1]
        if len(cur.children) == 0 or id(cur) in visited:
            if not match(ops[i], stack.pop()):
                return None
            i += 1
            continue
        stack.extend(reversed([c for c in cur.children]))
        visited.add(id(cur))

    return node

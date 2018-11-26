
import collections

from typing import Generic, Generator, Iterable
from typing import Optional, Tuple, TypeVar, Sequence

K = TypeVar('K')

class Tree(Generic[K]):

    def __init__(self, key: K, children: Iterable['Tree[K]']=tuple()) -> None:
        self._key = key
        self._children = tuple(children)
        self._hash: Optional[int] = None
        self._len: Optional[int] = None

    @property
    def key(self) -> K:
        return self._key

    @property
    def children(self) -> Tuple['Tree[K]']:
        return self._children

    def with_children(self, children: Iterable['Tree[K]']) -> 'Tree[K]':
        return self.__class__(key=self.key, children=tuple(children))

    def __eq__(self, other: 'Tree[K]') -> bool:
        if other is None:
            return False
        if self.key != other.key:
            return False
        return self.children == other.children

    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash((self.key, self.children))
        return self._hash

    def __len__(self) -> int:
        if self._len is None:
            self._len = 1
            if len(self.children) > 0:
                self._len += sum((len(c) for c in self.children))
        return self._len

    def __repr__(self) -> str:
        return '%s(key=%s, children=%s)' % (self.__class__.__name__, self.key, self.children)

    def __getstate__(self):
        return {'key': self.key, 'children': self.children}

    def __setstate__(self, state):
        self._key = state['key']
        self._children = state['children']
        self._hash = None
        self._len = None

    def __iter__(self) -> Generator['Tree[K]',None,None]:
        stack: collections.deque = collections.deque()
        stack.append(self)
        while stack:
            n = stack.pop()
            yield n
            stack.extend(n.children)

    def __copy__(self) -> 'Tree[K]':
        return self.__class__(
            key=self.key,
            children=(c.__copy__() for c in self.children)
        )

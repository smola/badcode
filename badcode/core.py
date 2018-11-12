
import typing

import bblfsh

class File:
    def __init__(self,
            path: str,
            hash: str,
            content: str,
            uast: bblfsh.Node) -> None:
        self._path = path
        self._hash = hash,
        self._content = content
        self._uast = uast

    @property
    def path(self) -> str:
        return self._path
    
    @property
    def hash(self) -> str:
        return self._hash

    @property
    def content(self) -> str:
        return self._content
    
    @property
    def uast(self) -> bblfsh.Node:
        return self._uast

    def __repr__(self) -> str:
        return 'File(hash=%s, path=%s)' % (self.hash, self.path)

class Change:
    def __init__(self,
        commit_id: str,
        base: File,
        head: File,
        deleted_lines: typing.Iterable[int],
        added_lines: typing.Iterable[int]) -> None:
        self._commit_id = commit_id
        self._base = base
        self._head = head
        self._deleted_lines = set(deleted_lines)
        self._added_lines = set(added_lines)

    @property
    def commit_id(self):
        return self._commit_id

    @property
    def base(self):
        return self._base

    @property
    def head(self):
        return self._head

    @property
    def deleted_lines(self) -> typing.Set[int]:
        return self._deleted_lines

    @property
    def added_lines(self) -> typing.Set[int]:
        return self._added_lines

    def __repr__(self) -> str:
        return 'Change(commit_id=%s, base=%s, head=%s, deleted_lines=%s, added_lines=%s)' % (
            self.commit_id, self.base, self.head,
            ','.join(map(str, self.deleted_lines)),
            ','.join(map(str, self.added_lines))
        )



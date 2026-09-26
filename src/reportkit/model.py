"""Output-independent report structure."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable


@dataclass(eq=False)
class Node:
    _parent: Container | None = field(default=None, init=False, repr=False)


@dataclass(eq=False)
class Container(Node):
    _children: tuple[Node, ...] = field(default=(), init=False, repr=False)

    @property
    def children(self) -> tuple[Node, ...]:
        return self._children

    def append(self, node: Node) -> Node:
        if not isinstance(node, Node):
            raise TypeError('A container accepts report nodes only')
        if isinstance(node, Document):
            raise ValueError('A document cannot be nested inside another container')
        if node is self or node._parent is not None:
            raise ValueError('A node can belong to only one container')
        node._parent = self
        self._children += (node,)
        return node


@dataclass(eq=False)
class Document(Container):
    title: str | None = None
    description: str | None = None
    author: str | None = None
    date: date | datetime | str | None = None

    def __post_init__(self) -> None:
        for name in ('title', 'description', 'author'):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f'{name} must be a string or None')
        if self.date is not None and not isinstance(self.date, (date, datetime, str)):
            raise TypeError('date must be a date, datetime, string, or None')


@dataclass(eq=False)
class Markdown(Node):
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError('markdown content must be a string')


@dataclass(eq=False)
class RawHTML(Node):
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError('raw HTML content must be a string')


@dataclass(eq=False)
class List(Node):
    items: Iterable[str | list | tuple]
    ordered: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.items, (str, bytes)):
            raise TypeError('list items must be an iterable of strings')
        if not isinstance(self.ordered, bool):
            raise TypeError('ordered must be a boolean')
        self.items = self._normalize(self.items)

    @classmethod
    def _normalize(cls, items: Iterable) -> tuple:
        result = []
        for item in items:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, (list, tuple)):
                if not result or not isinstance(result[-1], str):
                    raise ValueError('a nested list must follow a string item')
                result.append(cls._normalize(item))
            else:
                raise TypeError('list items must be strings or nested lists')
        return tuple(result)


@dataclass(eq=False)
class Artifact(Node):
    value: Any
    caption: str | None = None

    def __post_init__(self) -> None:
        if self.caption is not None and not isinstance(self.caption, str):
            raise TypeError('caption must be a string or None')


@dataclass(eq=False)
class Section(Container):
    title: str
    level: int = field(default=2, kw_only=True)

    def __post_init__(self) -> None:
        if not isinstance(self.title, str):
            raise TypeError('section title must be a string')
        if (
            isinstance(self.level, bool)
            or not isinstance(self.level, int)
            or not 1 <= self.level <= 6
        ):
            raise ValueError('section level must be an integer from 1 to 6')


@dataclass(eq=False)
class Panel(Container):
    title: str

    def __post_init__(self) -> None:
        if not isinstance(self.title, str):
            raise TypeError('panel title must be a string')


@dataclass(eq=False)
class Columns(Container):
    count: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.count, bool)
            or not isinstance(self.count, int)
            or self.count < 1
        ):
            raise ValueError('column count must be a positive integer')

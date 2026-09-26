"""Python composition frontend."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator, Iterable

from .model import Artifact, Columns, Container, Document, Heading, List, Markdown, Section


class Report:
    def __init__(
        self,
        title: str | None = None,
        *,
        description: str | None = None,
        author: str | None = None,
        date: date | datetime | str | None = None,
    ) -> None:
        self.document = Document(title=title, description=description, author=author, date=date)
        self._stack: list[Container] = [self.document]

    def _append(self, node: Any) -> Any:
        return self._stack[-1].append(node)

    def heading(self, level: int, title: str) -> Heading:
        return self._append(Heading(level=level, title=title))

    def markdown(self, content: str) -> Markdown:
        return self._append(Markdown(content=content))

    def list(self, items: Iterable[str], *, ordered: bool = False) -> List:
        return self._append(List(items=items, ordered=ordered))

    def add(self, value: Any, *, caption: str | None = None) -> Artifact:
        return self._append(Artifact(value=value, caption=caption))

    @contextmanager
    def section(self, title: str) -> Iterator[Section]:
        node = self._append(Section(title=title))
        self._stack.append(node)
        try:
            yield node
        finally:
            self._stack.pop()

    @contextmanager
    def columns(self, count: int) -> Iterator[Columns]:
        node = self._append(Columns(count=count))
        self._stack.append(node)
        try:
            yield node
        finally:
            self._stack.pop()

    def to_html(self, *, fragment: bool = False) -> str:
        from .writer import HTMLWriter

        return HTMLWriter().render(self.document, fragment=fragment)

    def write(self, path: str | Path, *, fragment: bool = False) -> Path:
        from .writer import HTMLWriter

        return HTMLWriter().write(self.document, path, fragment=fragment)

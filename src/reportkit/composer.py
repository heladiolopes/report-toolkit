"""Python composition frontend."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from copy import copy
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from .model import (
    Artifact,
    Columns,
    Container,
    Document,
    List,
    Markdown,
    Panel,
    RawHTML,
    Section,
)

_UNSET = object()

if TYPE_CHECKING:
    from .themes import Style


class Report:
    @classmethod
    def from_template(
        cls,
        path: str | Path,
        *,
        context: Mapping[str, Any] | None = None,
        title=_UNSET,
        description=_UNSET,
        author=_UNSET,
        date=_UNSET,
    ) -> Report:
        """Compose a report from a UTF-8 Markdown template file."""
        from ._template import compose

        path = Path(path)
        return compose(
            cls,
            path.read_text(encoding='utf-8'),
            context,
            str(path),
            {
                key: value
                for key, value in {
                    'title': title,
                    'description': description,
                    'author': author,
                    'date': date,
                }.items()
                if value is not _UNSET
            },
        )

    @classmethod
    def from_template_string(
        cls,
        source: str,
        *,
        context: Mapping[str, Any] | None = None,
        title=_UNSET,
        description=_UNSET,
        author=_UNSET,
        date=_UNSET,
    ) -> Report:
        """Compose a report from Markdown template text."""
        from ._template import compose

        return compose(
            cls,
            source,
            context,
            '<template>',
            {
                key: value
                for key, value in {
                    'title': title,
                    'description': description,
                    'author': author,
                    'date': date,
                }.items()
                if value is not _UNSET
            },
        )

    def __init__(
        self,
        title: str | None = None,
        *,
        description: str | None = None,
        author: str | None = None,
        date: date | datetime | str | None = None,
    ) -> None:
        self.document = Document(
            title=title, description=description, author=author, date=date
        )
        self._stack: list[Container] = [self.document]
        self._sections: list[list[Section]] = [[]]

    def _current_container(self) -> Container:
        sections = self._sections[-1]
        return sections[-1] if sections else self._stack[-1]

    def _append(self, node: Any) -> Any:
        return self._current_container().append(node)

    def heading(self, level: int, title: str, *, normalize: bool = False) -> Section:
        """Start a section lasting until an equal or shallower heading in this scope."""
        if not isinstance(normalize, bool):
            raise TypeError('normalize must be a boolean')
        node = Section(title=title, level=level)
        if normalize:
            node.title = ' '.join(
                title.replace('-', ' ').replace('_', ' ').split()
            ).title()
        sections = self._sections[-1]
        while sections and sections[-1].level >= level:
            sections.pop()
        self._append(node)
        sections.append(node)
        return node

    def markdown(self, content: str) -> Markdown:
        return self._append(Markdown(content=content))

    def paragraph(self, text: str) -> Markdown:
        return self.markdown(text)

    def list(self, items: Iterable, *, ordered: bool = False) -> List:
        return self._append(List(items=items, ordered=ordered))

    def ordered(self, items: Iterable) -> List:
        return self.list(items, ordered=True)

    def unordered(self, items: Iterable) -> List:
        return self.list(items, ordered=False)

    def raw_html(self, content: str) -> RawHTML:
        return self._append(RawHTML(content=content))

    def add(
        self,
        value: Any,
        *,
        caption: str | None = None,
        width: Literal['native', 'full'] = 'native',
        center: bool = True,
        expand: Literal['auto', 'always', 'never'] = 'auto',
    ) -> Artifact | RawHTML:
        node = Artifact(
            value=value,
            caption=caption,
            width=width,
            center=center,
            expand=expand,
        )
        if isinstance(value, str):
            if caption is not None:
                raise ValueError('raw HTML strings do not accept a caption')
            if width != 'native' or not center or expand != 'auto':
                raise ValueError('raw HTML strings do not accept artifact options')
            return self.raw_html(value)
        return self._append(node)

    def concat(self, other: Report) -> Report:
        if not isinstance(other, Report):
            raise TypeError('can only concatenate another Report')
        result = Report(
            self.document.title,
            description=self.document.description,
            author=self.document.author,
            date=self.document.date,
        )
        for source in (self.document, other.document):
            for node in source.children:
                result.document.append(self._copy_node(node))
        return result

    def __add__(self, other: Report) -> Report:
        return self.concat(other)

    @staticmethod
    def _copy_node(node: Any) -> Any:
        copied = copy(node)
        copied._parent = None
        if isinstance(copied, Container):
            copied._children = ()
            for child in node.children:
                copied.append(Report._copy_node(child))
        return copied

    @contextmanager
    def _scope(self, node: Container) -> Iterator[None]:
        self._append(node)
        self._stack.append(node)
        self._sections.append([])
        try:
            yield
        finally:
            self._sections.pop()
            self._stack.pop()

    @contextmanager
    def section(self, title: str) -> Iterator[Section]:
        parent = self._current_container()
        while parent is not None and not isinstance(parent, Section):
            parent = parent._parent
        level = min(parent.level + 1, 6) if parent is not None else 1
        node = Section(title=title, level=level)
        with self._scope(node):
            yield node

    @contextmanager
    def columns(self, count: int) -> Iterator[Columns]:
        node = Columns(count=count)
        with self._scope(node):
            yield node

    @contextmanager
    def panel(self, title: str) -> Iterator[Panel]:
        node = Panel(title=title)
        with self._scope(node):
            yield node

    def to_tree(self) -> str:
        """Return a readable node hierarchy without rendering artifact values."""
        from ._tree import format_tree

        return format_tree(self.document)

    def to_html(
        self,
        *,
        fragment: bool = False,
        pretty: bool = False,
        toc: bool = False,
        toc_depth: int = 6,
        numbered_headings: bool = False,
        toc_position: Literal['top', 'sidebar'] = 'top',
        style: Style | Mapping[str, object] | None = None,
    ) -> str:
        from .writer import HTMLWriter

        return HTMLWriter(
            pretty=pretty,
            toc=toc,
            toc_depth=toc_depth,
            style=style,
            numbered_headings=numbered_headings,
            toc_position=toc_position,
        ).render(self.document, fragment=fragment)

    def write(
        self,
        path: str | Path,
        *,
        fragment: bool = False,
        pretty: bool = False,
        toc: bool = False,
        toc_depth: int = 6,
        numbered_headings: bool = False,
        toc_position: Literal['top', 'sidebar'] = 'top',
        style: Style | Mapping[str, object] | None = None,
    ) -> Path:
        from .writer import HTMLWriter

        return HTMLWriter(
            pretty=pretty,
            toc=toc,
            toc_depth=toc_depth,
            style=style,
            numbered_headings=numbered_headings,
            toc_position=toc_position,
        ).write(self.document, path, fragment=fragment)

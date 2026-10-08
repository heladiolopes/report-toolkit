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
    from .profiles import RenderingProfile
    from .themes import Style


class Report:
    """Compose analytical content and render it as an HTML report.

    Parameters
    ----------
    title : str or None, optional
        Report title, displayed above the content and used as the browser title.
    description : str or None, optional
        Short description displayed below the report title.
    author : str or None, optional
        Report author metadata.
    date : datetime.date, datetime.datetime, str, or None, optional
        Report date metadata.

    Notes
    -----
    Content is appended in order. Use headings and layout context managers to
    build a hierarchy. Rendering-specific options are accepted by :meth:`to_html`
    and :meth:`write`.
    """

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
        """Compose a report from a UTF-8 Markdown template file.

        Parameters
        ----------
        path : str or pathlib.Path
            Path to the template file.
        context : mapping, optional
            Values available to template substitutions.
        title, description, author, date : optional
            Metadata overrides. Omitted values use template front matter;
            explicitly passing ``None`` clears the corresponding value.

        Returns
        -------
        Report
            A report composed from the template.

        Raises
        ------
        OSError
            If the template cannot be read.
        TemplateError
            If template syntax or context usage is invalid.
        """
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
        """Compose a report from Markdown template text.

        Parameters
        ----------
        source : str
            Markdown template text.
        context : mapping, optional
            Values available to template substitutions.
        title, description, author, date : optional
            Metadata overrides. Omitted values use template front matter;
            explicitly passing ``None`` clears the corresponding value.

        Returns
        -------
        Report
            A report composed from the template.

        Raises
        ------
        TemplateError
            If template syntax or context usage is invalid.
        """
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
        """Create an empty report with optional metadata.

        Parameters
        ----------
        title : str or None, optional
            Report title. If omitted, no visible title is rendered.
        description : str or None, optional
            Description displayed beneath the title.
        author : str or None, optional
            Author metadata.
        date : datetime.date, datetime.datetime, str, or None, optional
            Date metadata.

        Raises
        ------
        TypeError
            If a metadata value has an unsupported type.
        """
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
        """Start a structural section in the current composition scope.

        The section continues until an equal or shallower heading starts in the
        same scope. Deeper levels nest; skipped levels do not create sections.

        Parameters
        ----------
        level : int
            Heading level from 1 through 6.
        title : str
            Section title.
        normalize : bool, optional
            Replace underscores and hyphens with spaces, collapse whitespace,
            and apply title case.

        Returns
        -------
        Section
            The appended section node.

        Raises
        ------
        TypeError
            If ``title`` is not a string or ``normalize`` is not a boolean.
        ValueError
            If ``level`` is outside 1 through 6.
        """
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
        """Append Markdown content.

        Parameters
        ----------
        content : str
            Markdown text to render.

        Returns
        -------
        Markdown
            The appended content node.

        Raises
        ------
        TypeError
            If ``content`` is not a string.
        """
        return self._append(Markdown(content=content))

    def paragraph(self, text: str) -> Markdown:
        """Append a paragraph as Markdown.

        Parameters
        ----------
        text : str
            Paragraph text.

        Returns
        -------
        Markdown
            The appended content node.
        """
        return self.markdown(text)

    def list(self, items: Iterable, *, ordered: bool = False) -> List:
        """Append a list containing strings and optional nested lists.

        Parameters
        ----------
        items : iterable
            String items, optionally followed by nested lists or tuples.
        ordered : bool, optional
            Whether to render an ordered list.

        Returns
        -------
        List
            The appended list node.

        Raises
        ------
        TypeError
            If the items or ``ordered`` value has an unsupported type.
        ValueError
            If a nested list does not follow a string item.
        """
        return self._append(List(items=items, ordered=ordered))

    def ordered(self, items: Iterable) -> List:
        """Append an ordered list.

        Parameters
        ----------
        items : iterable
            String items, optionally followed by nested lists or tuples. See
            :meth:`list` for nesting rules.

        Returns
        -------
        List
            The appended list node.
        """
        return self.list(items, ordered=True)

    def unordered(self, items: Iterable) -> List:
        """Append an unordered list.

        Parameters
        ----------
        items : iterable
            String items, optionally followed by nested lists or tuples. See
            :meth:`list` for nesting rules.

        Returns
        -------
        List
            The appended list node.
        """
        return self.list(items, ordered=False)

    def raw_html(self, content: str) -> RawHTML:
        """Append trusted, unescaped HTML.

        Parameters
        ----------
        content : str
            HTML markup inserted as supplied.

        Returns
        -------
        RawHTML
            The appended HTML node.

        Raises
        ------
        TypeError
            If ``content`` is not a string.
        """
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
        """Append an analytical object or a raw HTML string.

        Parameters
        ----------
        value : object or str
            Object handled by a registered artifact adapter, or trusted HTML.
        caption : str or None, optional
            Escaped caption rendered beneath an artifact.
        width : {'native', 'full'}, optional
            Preserve intrinsic sizing or fit the artifact to its available width.
        center : bool, optional
            Center artifacts that fit in their viewport.
        expand : {'auto', 'always', 'never'}, optional
            Whether to offer an expanded artifact preview.

        Returns
        -------
        Artifact or RawHTML
            The appended node. Strings are inserted as raw HTML.

        Raises
        ------
        TypeError
            If the caption or centering option has an unsupported type.
        ValueError
            If an option is invalid or artifact options are supplied for a string.
        """
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
        """Return a new report containing this report followed by ``other``.

        Structure is copied while artifact values remain shared. The result
        preserves this report's metadata; neither source is modified.

        Parameters
        ----------
        other : Report
            Report whose content is appended.

        Returns
        -------
        Report
            A new combined report.

        Raises
        ------
        TypeError
            If ``other`` is not a :class:`Report`.
        """
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
        """Return this report concatenated with another report.

        Parameters
        ----------
        other : Report
            Report whose content is appended.

        Returns
        -------
        Report
            A new combined report. See :meth:`concat` for copy semantics.

        Raises
        ------
        TypeError
            If ``other`` is not a :class:`Report`.
        """
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
        """Group content under a structural section.

        The section level is one deeper than its nearest enclosing section,
        starting at level 1 and capped at level 6. The previous composition
        scope is restored when the context exits, including after an exception.

        Parameters
        ----------
        title : str
            Section title.

        Yields
        ------
        Section
            The section being composed.

        Raises
        ------
        TypeError
            If ``title`` is not a string.
        """
        parent = self._current_container()
        while parent is not None and not isinstance(parent, Section):
            parent = parent._parent
        level = min(parent.level + 1, 6) if parent is not None else 1
        node = Section(title=title, level=level)
        with self._scope(node):
            yield node

    @contextmanager
    def columns(self, count: int) -> Iterator[Columns]:
        """Group immediate children into a responsive column layout.

        Each immediate child is one grid item; additional items wrap.
        The previous composition scope is restored when the context exits.

        Parameters
        ----------
        count : int
            Number of columns; must be a positive integer.

        Yields
        ------
        Columns
            The columns container being composed.

        Raises
        ------
        ValueError
            If ``count`` is not a positive integer or is a boolean.
        """
        node = Columns(count=count)
        with self._scope(node):
            yield node

    @contextmanager
    def panel(self, title: str) -> Iterator[Panel]:
        """Group content beneath a panel label.

        The previous composition scope is restored when the context exits.

        Parameters
        ----------
        title : str
            Panel label. It is not a structural section heading.

        Yields
        ------
        Panel
            The panel being composed.

        Raises
        ------
        TypeError
            If ``title`` is not a string.
        """
        node = Panel(title=title)
        with self._scope(node):
            yield node

    def to_tree(self) -> str:
        """Return a readable summary of the report structure.

        Artifact values are not rendered; their types and captions are shown
        instead.

        Returns
        -------
        str
            A formatted node hierarchy.
        """
        from ._tree import format_tree

        return format_tree(self.document)

    def to_html(
        self,
        *,
        fragment: bool = False,
        pretty: bool = False,
        toc: bool = False,
        toc_depth: int = 6,
        collapsible_toc: bool = False,
        numbered_headings: bool = False,
        toc_position: Literal['top', 'sidebar', 'reader'] = 'top',
        style: Style | Mapping[str, object] | None = None,
        profile: str | RenderingProfile = 'rich',
    ) -> str:
        """Render the report as a complete HTML document or fragment.

        Parameters
        ----------
        fragment : bool, optional
            Return scoped styles, report content, and required runtime scripts
            without an HTML document wrapper.
        pretty : bool, optional
            Indent Reportkit's structural markup with two spaces.
        toc : bool, optional
            Include a table of contents for structural sections.
        collapsible_toc : bool, optional
            Enable branch controls in interactive themed TOCs (default False).
        toc_depth : int, optional
            Maximum absolute section level included in the TOC, from 1 to 6.
        numbered_headings : bool, optional
            Prefix structural headings and matching TOC entries with hierarchical
            numbers.
        toc_position : {'top', 'sidebar', 'reader'}, optional
            Place the TOC above the report, in a sidebar, or in a full-page
            reader layout. Reader mode requires toc=True, fragment=False, and
            a themed interactive profile.
        profile : str or RenderingProfile, optional
            Rendering capabilities: rich (default), portable, content, or a custom profile.
        style : Style, mapping, or None, optional
            Theme, palette, and display mode configuration.

        Returns
        -------
        str
            Rendered HTML.

        Raises
        ------
        TypeError
            If a boolean option or style value has an unsupported type.
        ValueError
            If ``toc_depth`` or ``toc_position`` is invalid.
        """
        from .writer import HTMLWriter

        return HTMLWriter(
            pretty=pretty,
            toc=toc,
            toc_depth=toc_depth,
            collapsible_toc=collapsible_toc,
            style=style,
            profile=profile,
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
        collapsible_toc: bool = False,
        numbered_headings: bool = False,
        toc_position: Literal['top', 'sidebar', 'reader'] = 'top',
        style: Style | Mapping[str, object] | None = None,
        profile: str | RenderingProfile = 'rich',
    ) -> Path:
        """Render the report and write UTF-8 HTML to a file.

        Parameters
        ----------
        path : str or pathlib.Path
            Destination file. Existing files are overwritten; parent directories
            are not created.
        fragment, pretty, toc, toc_depth, collapsible_toc, numbered_headings, toc_position, style, profile
            See :meth:`to_html` for the rendering options.

        Returns
        -------
        pathlib.Path
            The destination path.

        Raises
        ------
        OSError
            If the destination cannot be written.
        TypeError, ValueError
            If rendering options are invalid; see :meth:`to_html`.
        """
        from .writer import HTMLWriter

        return HTMLWriter(
            pretty=pretty,
            toc=toc,
            toc_depth=toc_depth,
            collapsible_toc=collapsible_toc,
            style=style,
            profile=profile,
            numbered_headings=numbered_headings,
            toc_position=toc_position,
        ).write(self.document, path, fragment=fragment)

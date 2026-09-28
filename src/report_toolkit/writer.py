"""HTML writer for report documents."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Mapping
from datetime import date, datetime
from functools import cache
from html import escape
from importlib.resources import files
from pathlib import Path
from typing import Literal

import mistune

from .adapters import AdapterRegistry, default_registry
from .model import (
    Artifact,
    Columns,
    Container,
    Document,
    List,
    Markdown,
    Node,
    Panel,
    RawHTML,
    Section,
)
from .themes import Style
from .themes.style import _resolve_style

_logger = logging.getLogger(__name__)
_Outline = dict[Section, tuple[int, str, str]]
_TOCEntry = tuple[str, list['_TOCEntry']]


class _Payload(str):
    """Opaque content whose boundaries must not gain formatting whitespace."""


@cache
def _base_css() -> str:
    """Read packaged CSS once, including when imported from a wheel archive."""
    return (
        files('report_toolkit')
        .joinpath('resources/report.css')
        .read_text(encoding='utf-8')
        .strip()
    )


def _style_id(style: Style) -> str:
    # Resolved content distinguishes custom objects even when names are reused.
    payload = (
        style.theme.name,
        dict(style.theme.tokens),
        style.theme.css,
        style.palette.name,
        dict(style.palette.light),
        dict(style.palette.dark),
        style.mode,
    )
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def _stylesheet(style: Style, *, fragment: bool) -> str:
    # :where keeps specificity low enough for Pandas Styler's explicit rules.
    selector = f'.reporttkt:where([data-reporttkt-theme="{_style_id(style)}"])'
    base = re.sub(r'\.reporttkt(?![\w-])', lambda match: selector, _base_css())

    def variables(tokens: Mapping[str, str], mode: str) -> str:
        declarations = '\n'.join(
            f'  --reporttkt-{key.replace("_", "-")}: {value};'
            for key, value in sorted(tokens.items())
        )
        rules = f'{selector} {{\n{declarations}\n  color-scheme: {mode};\n}}'
        if not fragment:
            rules += (
                '\nbody { margin: 0; background: '
                + tokens['page_background']
                + f'; color-scheme: {mode}; }}'
            )
        return rules

    mode = 'light' if style.mode == 'auto' else style.mode
    tokens = dict(style.theme.tokens) | dict(getattr(style.palette, mode))
    css = variables(tokens, mode) + '\n' + base
    if style.mode == 'auto':
        css += (
            '\n@media (prefers-color-scheme: dark) {\n'
            + variables(style.palette.dark, 'dark')
            + '\n}'
        )
    css += '\n' + style.theme.css.replace('&', selector)
    # Prevent a CSS string from terminating the surrounding HTML style element.
    return css.replace('<', r'\3c ')


def _format_size(size: int) -> str:
    if size < 1024:
        return f'{size} B'
    value = float(size)
    for unit in ('KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB'):
        value /= 1024
        if value < 1024 or unit == 'EiB':
            return f'{value:.1f} {unit}'


class HTMLWriter:
    """Render output-independent report documents as HTML.

    Parameters
    ----------
    registry : AdapterRegistry or None, optional
        Registry used to render analytical objects. If omitted, the default
        adapters are registered.
    style : Style, mapping, or None, optional
        Structural theme, color palette, and display mode. Mappings accept the
        fields ``theme``, ``palette``, and ``mode``.
    inline_altair : bool, optional
        Embed Altair's JavaScript bundle instead of loading it from a CDN.
        Requires ``vl-convert-python``. Cannot be combined with ``registry``.
    pretty : bool, optional
        Indent Reportkit's structural markup with two spaces.
    toc : bool, optional
        Include a table of contents for structural sections.
    toc_depth : int, optional
        Maximum absolute section level included in the TOC, from 1 to 6.
    numbered_headings : bool, optional
        Prefix structural headings and matching TOC entries with hierarchical
        numbers.
    toc_position : {'top', 'sidebar'}, optional
        Place the TOC above the report or in a sidebar.

    Raises
    ------
    TypeError
        If boolean options or ``style`` have unsupported types.
    ValueError
        If ``toc_depth`` or ``toc_position`` is invalid, or both a custom
        registry and ``inline_altair`` are supplied.
    """

    def __init__(
        self,
        *,
        registry: AdapterRegistry | None = None,
        style: Style | Mapping[str, object] | None = None,
        inline_altair: bool = False,
        pretty: bool = False,
        toc: bool = False,
        toc_depth: int = 6,
        numbered_headings: bool = False,
        toc_position: Literal['top', 'sidebar'] = 'top',
    ) -> None:
        if not isinstance(pretty, bool):
            raise TypeError('pretty must be a boolean')
        self.pretty = pretty
        if not isinstance(toc, bool):
            raise TypeError('toc must be a boolean')
        if (
            isinstance(toc_depth, bool)
            or not isinstance(toc_depth, int)
            or not 1 <= toc_depth <= 6
        ):
            raise ValueError('toc_depth must be an integer from 1 to 6')
        if not isinstance(numbered_headings, bool):
            raise TypeError('numbered_headings must be a boolean')
        if toc_position not in ('top', 'sidebar'):
            raise ValueError("toc_position must be 'top' or 'sidebar'")
        self.numbered_headings = numbered_headings
        self.toc_position = toc_position
        self.style = _resolve_style(style)
        self.toc = toc
        self.toc_depth = toc_depth
        if registry is not None and inline_altair:
            raise ValueError('Choose a custom registry or inline_altair, not both')
        self.registry = (
            registry
            if registry is not None
            else default_registry(inline_altair=inline_altair)
        )
        self._markdown = mistune.create_markdown(escape=True)

    def _block(
        self, opening: str, children: list[str], closing: str, depth: int
    ) -> str:
        if not self.pretty:
            return opening + ''.join(children) + closing
        # Indent only owned boundaries: embedded payloads remain byte-for-byte intact.
        padding = '  ' * depth
        parts = [opening]
        previous_payload = False
        for child in filter(None, children):
            payload = isinstance(child, _Payload)
            if not payload and not previous_payload:
                parts.append('\n' + padding + '  ')
            parts.append(child)
            previous_payload = payload
        if not previous_payload:
            parts.append('\n' + padding)
        parts.append(closing)
        return ''.join(parts)

    def render(self, document: Document, *, fragment: bool = False) -> str:
        """Render a document as a complete HTML page or embeddable fragment.

        Parameters
        ----------
        document : Document
            Report document to render.
        fragment : bool, optional
            Return scoped CSS, body content, and required artifact scripts
            without an HTML document wrapper.

        Returns
        -------
        str
            Rendered HTML.

        Raises
        ------
        TypeError
            If ``document`` is not a :class:`~report_toolkit.model.Document`.
        TypeError, ValueError
            If an artifact has no registered adapter or cannot be rendered.
        """
        if not isinstance(document, Document):
            raise TypeError('HTMLWriter.render expects a Document')
        depth = 0 if fragment else 2
        content = self._render_document(document, depth)
        css = _stylesheet(self.style, fragment=fragment)
        stylesheet = f'<style>{css}</style>'
        runtime = ''
        if self._has_artifacts(document):
            script = (
                files('report_toolkit')
                .joinpath('resources/artifacts.js')
                .read_text(encoding='utf-8')
            )
            runtime = f'<script>{script}</script>'
        if fragment:
            return ('\n' if self.pretty else '').join(
                part for part in (stylesheet, content, runtime) if part
            )
        title = document.title if document.title is not None else 'Report'
        head = self._block(
            '<head>',
            [
                '<meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                f'<title>{escape(title)}</title>',
                stylesheet,
            ],
            '</head>',
            1,
        )
        body = self._block('<body>', [content, runtime], '</body>', 1)
        return (
            '<!doctype html>'
            + ('\n' if self.pretty else '')
            + self._block('<html lang="en">', [head, body], '</html>', 0)
            + ('\n' if self.pretty else '')
        )

    @staticmethod
    def _has_artifacts(node: Node) -> bool:
        return isinstance(node, Artifact) or (
            isinstance(node, Container)
            and any(HTMLWriter._has_artifacts(child) for child in node.children)
        )

    def write(
        self, document: Document, path: str | Path, *, fragment: bool = False
    ) -> Path:
        """Render a document and write UTF-8 HTML to a file.

        Parameters
        ----------
        document : Document
            Report document to render.
        path : str or pathlib.Path
            Destination file. Existing files are overwritten; parent directories
            are not created.
        fragment : bool, optional
            Write an embeddable fragment instead of a complete HTML page.

        Returns
        -------
        pathlib.Path
            The destination path.

        Raises
        ------
        OSError
            If the destination cannot be written.
        TypeError, ValueError
            If the document or one of its artifacts cannot be rendered.
        """
        destination = Path(path)
        destination.write_text(
            self.render(document, fragment=fragment), encoding='utf-8'
        )
        _logger.info(
            'Wrote report to %s (%s)',
            destination,
            _format_size(destination.stat().st_size),
        )
        return destination

    def _render_document(self, document: Document, depth: int = 0) -> str:
        outline = self._outline(document)
        navigation = self._render_toc(outline) if self.toc else ''
        # Section slugs never contain underscores, so this TOC ID cannot collide.
        backlink = (
            ' <a class="report-toc-backlink" href="#reporttkt_toc" '
            'aria-label="Back to table of contents">↑</a>'
            if navigation and self.toc_position == 'top'
            else ''
        )
        sidebar = bool(navigation and self.toc_position == 'sidebar')
        article_depth = depth + int(sidebar)
        body = [
            self._render_node(node, outline, backlink, article_depth + 1)
            for node in document.children
        ]
        parts = []
        if document.title is not None:
            parts.append(
                f'<header class="report-header"><h1 class="report-title">{escape(document.title)}</h1></header>'
            )
        if document.description is not None:
            parts.append(
                f'<p class="report-description">{escape(document.description)}</p>'
            )
        parts.extend(self._metadata(document))
        if navigation and self.toc_position == 'top':
            parts.append(navigation)
        parts.extend(body)
        content = self._block(
            f'<article class="reporttkt" data-reporttkt-theme="{_style_id(self.style)}">',
            parts,
            '</article>',
            article_depth,
        )
        if sidebar:
            return self._block(
                f'<div class="reporttkt report-layout" data-reporttkt-theme="{_style_id(self.style)}">',
                [
                    self._block(
                        '<div class="report-sidebar">',
                        [navigation],
                        '</div>',
                        depth + 1,
                    ),
                    content,
                ],
                '</div>',
                depth,
            )
        return content

    def _outline(self, document: Document) -> _Outline:
        """Collect heading levels, anchors, and display labels without changing the tree."""
        outline: _Outline = {}
        used: set[str] = set()
        # Counts belong to outline parents, not absolute HTML heading levels.
        stack: list[tuple[int, list[int], int]] = [(0, [], 0)]

        def visit(node: Node) -> None:
            if isinstance(node, Section):
                level = node.level
                slug = (
                    re.sub(r'[\W_]+', '-', node.title.lower()).strip('-') or 'heading'
                )
                base = f'reporttkt-{slug}'
                anchor = base
                suffix = 2
                while anchor in used:
                    anchor = f'{base}-{suffix}'
                    suffix += 1
                used.add(anchor)
                while stack[-1][0] >= level:
                    stack.pop()
                parent_level, prefix, count = stack[-1]
                count += 1
                stack[-1] = (parent_level, prefix, count)
                number = [*prefix, count]
                stack.append((level, number, 0))
                label = node.title
                if self.numbered_headings:
                    label = '.'.join(map(str, number)) + '. ' + label
                outline[node] = (level, anchor, label)
            if isinstance(node, Container):
                for child in node.children:
                    visit(child)

        visit(document)
        return outline

    def _render_toc(self, outline: _Outline) -> str:
        # Each entry holds its link and child entries; the stack tracks ancestors.
        entries: list[_TOCEntry] = []
        stack = [(0, entries)]
        for level, anchor, label in outline.values():
            if level > self.toc_depth:
                continue
            while stack[-1][0] >= level:
                stack.pop()
            children: list[_TOCEntry] = []
            link = f'<a href="#{anchor}">{escape(label)}</a>'
            stack[-1][1].append((link, children))
            stack.append((level, children))
        if not entries:
            return ''

        def render_entries(items: list[_TOCEntry]) -> str:
            return (
                '<ul>'
                + ''.join(
                    '<li>'
                    + link
                    + (render_entries(children) if children else '')
                    + '</li>'
                    for link, children in items
                )
                + '</ul>'
            )

        return (
            '<nav class="report-toc" id="reporttkt_toc" tabindex="-1" aria-label="Table of contents">'
            '<div class="report-toc-title">Table of contents</div>'
            + render_entries(entries)
            + '</nav>'
        )

    def _metadata(self, document: Document) -> list[str]:
        if document.author is None and document.date is None:
            return []
        parts = ['<div class="report-meta">']
        if document.author is not None:
            parts.append(f'<span>{escape(document.author)}</span>')
        if document.date is not None:
            value = (
                document.date.isoformat()
                if isinstance(document.date, (date, datetime))
                else document.date
            )
            parts.append(
                f'<time datetime="{escape(value, quote=True)}">{escape(value)}</time>'
            )
        parts.append('</div>')
        return parts

    def _render_node(
        self, node: Node, outline: _Outline, backlink: str = '', depth: int = 0
    ) -> str:
        if isinstance(node, Markdown):
            return _Payload(self._markdown(node.content).strip())
        if isinstance(node, RawHTML):
            return _Payload(node.content)
        if isinstance(node, List):
            return self._render_list(node.items, ordered=node.ordered)
        if isinstance(node, Artifact):
            rendered = self.registry.resolve(node.value).render(node.value)
            caption = (
                f'<figcaption>{escape(node.caption)}</figcaption>'
                if node.caption
                else ''
            )
            attributes = (
                f'data-width="{node.width}" data-center="{str(node.center).lower()}" '
                f'data-expand="{node.expand}" '
                f'data-kind="{escape(rendered.kind or "custom", quote=True)}"'
            )
            sizing = ''
            if rendered.native_width is not None:
                width = float(rendered.native_width)
                if not 0 < width < float('inf'):
                    raise ValueError('native_width must be finite and positive')
                sizing = f' style="--reporttkt-native-width: {width:g}px"'
            viewport = (
                '<div class="report-artifact-viewport" tabindex="0" aria-label="Artifact content">'
                '<div class="report-artifact-space"><div class="report-artifact-content"'
                + sizing
                + '>'
                + rendered.html
                + '</div></div></div>'
            )
            return self._block(
                f'<figure class="report-artifact" {attributes}>',
                [viewport, caption],
                '</figure>',
                depth,
            )
        if isinstance(node, Section):
            heading, anchor, label = outline[node]
            children = [
                self._render_node(child, outline, backlink, depth + 1)
                for child in node.children
            ]
            return self._block(
                '<section class="report-section">',
                [
                    f'<h{heading} id="{anchor}">{escape(label)}{backlink}</h{heading}>',
                    *children,
                ],
                '</section>',
                depth,
            )
        if isinstance(node, Panel):
            children = [
                self._render_node(child, outline, backlink, depth + 1)
                for child in node.children
            ]
            return self._block(
                '<div class="report-panel">',
                [
                    f'<div class="report-panel-title">{escape(node.title)}</div>',
                    *children,
                ],
                '</div>',
                depth,
            )
        if isinstance(node, Columns):
            children = [
                self._block(
                    '<div class="report-column-item">',
                    [self._render_node(child, outline, backlink, depth + 2)],
                    '</div>',
                    depth + 1,
                )
                for child in node.children
            ]
            return self._block(
                f'<div class="report-columns" style="--reporttkt-columns: {node.count}">',
                children,
                '</div>',
                depth,
            )
        raise TypeError(f'Cannot render node type {type(node).__name__}')

    def _render_list(self, items: tuple, *, ordered: bool) -> str:
        tag = 'ol' if ordered else 'ul'
        rendered = []
        index = 0
        while index < len(items):
            rendered.append(f'<li>{escape(items[index])}')
            if index + 1 < len(items) and isinstance(items[index + 1], tuple):
                rendered.append(self._render_list(items[index + 1], ordered=ordered))
                index += 1
            rendered.append('</li>')
            index += 1
        return f'<{tag}>{"".join(rendered)}</{tag}>'

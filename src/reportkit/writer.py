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


@cache
def _base_css() -> str:
    """Read packaged CSS once, including when imported from a wheel archive."""
    return (
        files('reportkit')
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
    selector = f'.reportkit:where([data-reportkit-theme="{_style_id(style)}"])'
    base = re.sub(r'\.reportkit(?![\w-])', lambda match: selector, _base_css())

    def variables(tokens: Mapping[str, str], mode: str) -> str:
        declarations = '\n'.join(
            f'  --reportkit-{key.replace("_", "-")}: {value};'
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
    def __init__(
        self,
        *,
        registry: AdapterRegistry | None = None,
        style: Style | Mapping[str, object] | None = None,
        inline_altair: bool = False,
        toc: bool = False,
        toc_depth: int = 6,
        numbered_headings: bool = False,
        toc_position: Literal['top', 'sidebar'] = 'top',
    ) -> None:
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

    def render(self, document: Document, *, fragment: bool = False) -> str:
        if not isinstance(document, Document):
            raise TypeError('HTMLWriter.render expects a Document')
        content = self._render_document(document)
        css = _stylesheet(self.style, fragment=fragment)
        if fragment:
            return f'<style>\n{css}\n</style>\n{content}'
        title = document.title if document.title is not None else 'Report'
        return (
            '<!doctype html>\n<html lang="en">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{escape(title)}</title>\n<style>\n{css}\n</style>\n'
            f'</head>\n<body>\n{content}\n</body>\n</html>\n'
        )

    def write(
        self, document: Document, path: str | Path, *, fragment: bool = False
    ) -> Path:
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

    def _render_document(self, document: Document) -> str:
        outline = self._outline(document)
        navigation = self._render_toc(outline) if self.toc else ''
        # Section slugs never contain underscores, so this TOC ID cannot collide.
        backlink = (
            ' <a class="report-toc-backlink" href="#reportkit_toc" '
            'aria-label="Back to table of contents">↑</a>'
            if navigation and self.toc_position == 'top'
            else ''
        )
        body = '\n'.join(
            self._render_node(node, outline, backlink) for node in document.children
        )
        parts = [
            f'<article class="reportkit" data-reportkit-theme="{_style_id(self.style)}">'
        ]
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
        parts.append(body)
        parts.append('</article>')
        content = '\n'.join(parts)
        if navigation and self.toc_position == 'sidebar':
            return (
                f'<div class="reportkit report-layout" data-reportkit-theme="{_style_id(self.style)}">'
                '<div class="report-sidebar">'
                + navigation
                + '</div>'
                + content
                + '</div>'
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
                base = f'reportkit-{slug}'
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
            '<nav class="report-toc" id="reportkit_toc" tabindex="-1" aria-label="Table of contents">'
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

    def _render_node(self, node: Node, outline: _Outline, backlink: str = '') -> str:
        if isinstance(node, Markdown):
            return self._markdown(node.content).strip()
        if isinstance(node, RawHTML):
            return node.content
        if isinstance(node, List):
            return self._render_list(node.items, ordered=node.ordered)
        if isinstance(node, Artifact):
            rendered = self.registry.resolve(node.value).render(node.value)
            caption = (
                f'<figcaption>{escape(node.caption)}</figcaption>'
                if node.caption
                else ''
            )
            return f'<figure class="report-artifact">{rendered.html}{caption}</figure>'
        if isinstance(node, Section):
            heading, anchor, label = outline[node]
            children = '\n'.join(
                self._render_node(child, outline, backlink) for child in node.children
            )
            return (
                f'<section class="report-section"><h{heading} id="{anchor}">{escape(label)}{backlink}</h{heading}>\n'
                f'{children}\n</section>'
            )
        if isinstance(node, Panel):
            children = '\n'.join(
                self._render_node(child, outline, backlink) for child in node.children
            )
            return (
                f'<div class="report-panel"><div class="report-panel-title">{escape(node.title)}</div>\n'
                f'{children}\n</div>'
            )
        if isinstance(node, Columns):
            children = '\n'.join(
                f'<div class="report-column-item">{self._render_node(child, outline, backlink)}</div>'
                for child in node.children
            )
            return (
                f'<div class="report-columns" style="--reportkit-columns: {node.count}">\n'
                f'{children}\n</div>'
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

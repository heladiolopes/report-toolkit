"""HTML writer for report documents."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from html import escape
from pathlib import Path

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

_logger = logging.getLogger(__name__)
_Outline = dict[Section, tuple[int, str]]
_TOCEntry = tuple[str, list['_TOCEntry']]


def _format_size(size: int) -> str:
    if size < 1024:
        return f'{size} B'
    value = float(size)
    for unit in ('KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB'):
        value /= 1024
        if value < 1024 or unit == 'EiB':
            return f'{value:.1f} {unit}'


_PAGE_CSS = 'body { margin: 0; background: #f4f6fa; }'
_CSS = """
.reportkit, .reportkit * { box-sizing: border-box; }
.reportkit { max-width: 1040px; margin: 32px auto; padding: 48px clamp(20px, 5vw, 72px); background: white; border: 1px solid #e5eaf0; border-radius: 12px; box-shadow: 0 12px 36px #1d29390c; }
.reportkit { color: #1d2939; font: 16px/1.65 system-ui, sans-serif; }
.reportkit h1, .reportkit h2, .reportkit h3, .reportkit h4, .reportkit h5, .reportkit h6 { color: #14233b; line-height: 1.25; margin: 1.7em 0 .55em; }
.reportkit h1 { font-size: 2.25rem; margin-top: 0; }
.reportkit .report-title { font-size: clamp(2.25rem, 5vw, 3rem); margin: 0 0 .5em; }
.reportkit h2 { font-size: 1.65rem; border-bottom: 1px solid #e5eaf0; padding-bottom: .25em; }
.reportkit p { margin: .6em 0 1.1em; }
.reportkit a { color: #1259a8; }
.reportkit .report-description { color: #52637a; font-size: 1.1rem; }
.reportkit .report-meta { color: #617189; font-size: .875rem; display: flex; flex-wrap: wrap; gap: 1.2rem; }
.reportkit .report-section { margin-top: 2rem; }
.reportkit .report-columns { display: grid; grid-template-columns: repeat(var(--reportkit-columns), minmax(0, 1fr)); gap: 1.5rem; align-items: start; }
.reportkit .report-column-item { min-width: 0; }
.reportkit .report-panel { min-width: 0; overflow-x: auto; }
.reportkit .report-panel-title { color: #14233b; font-weight: 650; margin-bottom: .75rem; }
.reportkit .report-toc { margin: 1.5rem 0; padding: 1rem 1.5rem; background: #f4f6fa; border-radius: 6px; }
.reportkit .report-toc-title { font-weight: 650; }
.reportkit .report-toc ul { padding-left: 1.5rem; }
.reportkit .report-artifact { margin: 1.5rem 0; min-width: 0; overflow-x: auto; }
.reportkit figcaption { color: #617189; font-size: .875rem; margin-top: .5rem; }
.reportkit .reportkit-figure-image { display: block; max-width: 100%; height: auto; }
.reportkit table { border-collapse: collapse; width: 100%; font-size: .9rem; }
.reportkit th, .reportkit td { border-bottom: 1px solid #e5eaf0; padding: .55rem .75rem; text-align: left; }
.reportkit th { background: #f7f9fc; font-weight: 650; }
.reportkit pre { overflow-x: auto; padding: 1rem; background: #f4f6fa; border-radius: 6px; }
.reportkit code { font-size: .9em; }
@media (max-width: 700px) { .reportkit { margin: 0; border: 0; border-radius: 0; padding: 24px 18px; } .reportkit .report-columns { grid-template-columns: 1fr; } }
""".strip()


class HTMLWriter:
    def __init__(
        self,
        *,
        registry: AdapterRegistry | None = None,
        inline_altair: bool = False,
        toc: bool = False,
        toc_depth: int = 6,
    ) -> None:
        if not isinstance(toc, bool):
            raise TypeError('toc must be a boolean')
        if (
            isinstance(toc_depth, bool)
            or not isinstance(toc_depth, int)
            or not 1 <= toc_depth <= 6
        ):
            raise ValueError('toc_depth must be an integer from 1 to 6')
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
        if fragment:
            return f'<style>\n{_CSS}\n</style>\n{content}'
        title = document.title if document.title is not None else 'Report'
        return (
            '<!doctype html>\n<html lang="en">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{escape(title)}</title>\n<style>\n{_PAGE_CSS}\n{_CSS}\n</style>\n'
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
            'Wrote report to %s (%s)', destination,
            _format_size(destination.stat().st_size),
        )
        return destination

    def _render_document(self, document: Document) -> str:
        outline = self._outline(document)
        body = '\n'.join(self._render_node(node, outline) for node in document.children)
        parts = ['<article class="reportkit">']
        if document.title is not None:
            parts.append(
                f'<header class="report-header"><h1 class="report-title">{escape(document.title)}</h1></header>'
            )
        if document.description is not None:
            parts.append(
                f'<p class="report-description">{escape(document.description)}</p>'
            )
        parts.extend(self._metadata(document))
        if self.toc:
            navigation = self._render_toc(outline)
            if navigation:
                parts.append(navigation)
        parts.append(body)
        parts.append('</article>')
        return '\n'.join(parts)

    def _outline(self, document: Document) -> _Outline:
        """Collect section levels and anchors without changing the tree."""
        outline: _Outline = {}
        used: set[str] = set()

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
                outline[node] = (level, anchor)
            if isinstance(node, Container):
                for child in node.children:
                    visit(child)

        visit(document)
        return outline

    def _render_toc(self, outline: _Outline) -> str:
        # Each entry holds its link and child entries; the stack tracks ancestors.
        entries: list[_TOCEntry] = []
        stack = [(0, entries)]
        for node, (level, anchor) in outline.items():
            if level > self.toc_depth:
                continue
            while stack[-1][0] >= level:
                stack.pop()
            children: list[_TOCEntry] = []
            link = f'<a href="#{anchor}">{escape(node.title)}</a>'
            stack[-1][1].append((link, children))
            stack.append((level, children))
        if not entries:
            return ''

        def render_entries(items: list[_TOCEntry]) -> str:
            return '<ul>' + ''.join(
                '<li>' + link + (render_entries(children) if children else '') + '</li>'
                for link, children in items
            ) + '</ul>'

        return (
            '<nav class="report-toc" aria-label="Table of contents">'
            '<div class="report-toc-title">Table of contents</div>'
            + render_entries(entries) + '</nav>'
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

    def _render_node(self, node: Node, outline: _Outline) -> str:
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
            heading, anchor = outline[node]
            children = '\n'.join(
                self._render_node(child, outline) for child in node.children
            )
            return (
                f'<section class="report-section"><h{heading} id="{anchor}">{escape(node.title)}</h{heading}>\n'
                f'{children}\n</section>'
            )
        if isinstance(node, Panel):
            children = '\n'.join(
                self._render_node(child, outline) for child in node.children
            )
            return (
                f'<div class="report-panel"><div class="report-panel-title">{escape(node.title)}</div>\n'
                f'{children}\n</div>'
            )
        if isinstance(node, Columns):
            children = '\n'.join(
                f'<div class="report-column-item">{self._render_node(child, outline)}</div>'
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

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
from html.parser import HTMLParser
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
from .profiles import RenderingProfile, _resolve_profile
from .themes import Style
from .themes.style import _resolve_style

_logger = logging.getLogger(__name__)
_Outline = dict[Section, tuple[int, str, str]]
_TOCEntry = tuple[str, str, list['_TOCEntry']]


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


def _stylesheet(style: Style, *, fragment: bool, reader: bool = False) -> str:
    # :where keeps specificity low enough for Pandas Styler's explicit rules.
    selector = f'.reporttkt:where([data-reporttkt-theme="{_style_id(style)}"])'
    base_css = _base_css()
    if reader:
        base_css += '\n' + files('report_toolkit').joinpath(
            'resources/reader.css'
        ).read_text(encoding='utf-8')
    base = re.sub(r'\.reporttkt(?![\w-])', lambda match: selector, base_css)

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
    if reader:
        for palette_mode in ('light', 'dark'):
            declarations = '\n'.join(
                f'--reporttkt-{key.replace("_", "-")}: {value};'
                for key, value in sorted(getattr(style.palette, palette_mode).items())
            )
            css += (
                f'\n{selector}[data-reader-theme="{palette_mode}"] '
                f'{{ {declarations} color-scheme: {palette_mode}; }}'
                f'\nbody[data-reader-theme="{palette_mode}"] '
                f'{{ background: {getattr(style.palette, palette_mode)["page_background"]}; '
                f'color-scheme: {palette_mode}; }}'
            )
    # Prevent a CSS string from terminating the surrounding HTML style element.
    return css.replace('<', r'\3c ')


class _ElementClasses(HTMLParser):
    """Locate opening tags without serializing embedded scripts or styles."""

    _attributes = re.compile(
        r"""\s+([^\s=/>]+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s>]+))?""", re.DOTALL
    )

    def __init__(self, html: str, classes: Mapping[str, tuple[str, ...]]) -> None:
        super().__init__(convert_charrefs=False)
        self.classes = classes
        self.edits: list[tuple[int, int, str]] = []
        self.offsets = [0]
        self.offsets.extend(match.end() for match in re.finditer('\n', html))
        self.feed(html)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        additions = self.classes.get(tag, ())
        if not additions:
            return
        opening = self.get_starttag_text()
        existing = next((value or '' for key, value in attrs if key == 'class'), '')
        tokens = existing.split()
        tokens.extend(token for token in additions if token not in tokens)
        attribute = 'class="' + escape(' '.join(tokens), quote=True) + '"'
        for match in self._attributes.finditer(opening):
            if match[1].lower() == 'class':
                opening = opening[: match.start(1)] + attribute + opening[match.end() :]
                break
        else:
            index = len(opening) - (2 if opening.endswith('/>') else 1)
            opening = opening[:index] + ' ' + attribute + opening[index:]
        line, column = self.getpos()
        start = self.offsets[line - 1] + column
        self.edits.append((start, start + len(self.get_starttag_text()), opening))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def _add_element_classes(html: str, classes: Mapping[str, tuple[str, ...]]) -> str:
    if not classes:
        return html
    parser = _ElementClasses(html, classes)
    parts = []
    previous = 0
    for start, end, replacement in parser.edits:
        parts.extend((html[previous:start], replacement))
        previous = end
    parts.append(html[previous:])
    return ''.join(parts)


@cache
def _layout_css() -> str:
    css = (
        files('report_toolkit')
        .joinpath('resources/layout.css')
        .read_text(encoding='utf-8')
        .strip()
    )
    return re.sub(
        r'\.reporttkt(?![\w-])', '.reporttkt:where([data-reporttkt-layout])', css
    )


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
    profile : str or RenderingProfile, optional
        Rendering capabilities: rich (default), portable, content, or a custom profile.
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
    collapsible_toc : bool, optional
        Enable branch controls in interactive themed TOCs (default False).
    toc_depth : int, optional
        Maximum absolute section level included in the TOC, from 1 to 6.
    numbered_headings : bool, optional
        Prefix structural headings and matching TOC entries with hierarchical
        numbers.
    toc_position : {'top', 'sidebar', 'reader'}, optional
        Place the TOC above the report, in a sidebar, or in a full-page
        reader layout. Reader mode requires toc=True and a themed interactive profile.

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
        profile: str | RenderingProfile = 'rich',
        inline_altair: bool = False,
        pretty: bool = False,
        toc: bool = False,
        toc_depth: int = 6,
        collapsible_toc: bool = False,
        numbered_headings: bool = False,
        toc_position: Literal['top', 'sidebar', 'reader'] = 'top',
    ) -> None:
        if not isinstance(pretty, bool):
            raise TypeError('pretty must be a boolean')
        if not isinstance(collapsible_toc, bool):
            raise TypeError('collapsible_toc must be a boolean')
        self.collapsible_toc = collapsible_toc
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
        if toc_position not in ('top', 'sidebar', 'reader'):
            raise ValueError("toc_position must be 'top', 'sidebar', or 'reader'")
        self.profile = _resolve_profile(profile)
        if toc_position not in self.profile.toc_positions:
            raise ValueError(
                f'Profile {self.profile.name!r} does not support {toc_position!r} TOC positioning'
            )
        if toc_position == 'reader':
            if not toc:
                raise ValueError('reader mode requires toc=True')
            if (
                self.profile.content_only
                or self.profile.stylesheet != 'theme'
                or self.profile.chart_mode != 'interactive'
            ):
                raise ValueError(
                    'reader mode requires a themed interactive full-page profile'
                )
        if inline_altair and self.profile.chart_mode == 'svg':
            raise ValueError('inline_altair cannot be used with SVG profiles')
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
        if fragment and self.toc_position == 'reader':
            raise ValueError('reader mode does not support fragments')
        fragment = fragment or self.profile.content_only
        depth = 0 if fragment else 2
        content = self._render_document(document, depth)
        css = (
            _stylesheet(
                self.style, fragment=fragment, reader=self.toc_position == 'reader'
            )
            if self.profile.stylesheet == 'theme'
            else _layout_css()
        )
        stylesheet = f'<style>{css}</style>'
        runtime = ''
        if self.profile.artifact_controls and self._has_artifacts(document):
            script = (
                files('report_toolkit')
                .joinpath('resources/artifacts.js')
                .read_text(encoding='utf-8')
            )
            runtime = f'<script>{script}</script>'
        if (
            self._navigation_enabled
            and self.toc
            and (
                self.toc_position == 'reader'
                or any(
                    level <= self.toc_depth
                    for level, _, _ in self._outline(document).values()
                )
            )
        ):
            script = (
                files('report_toolkit')
                .joinpath('resources/navigation.js')
                .read_text(encoding='utf-8')
            )
            runtime += f'<script>{script}</script>'
        if fragment:
            html = ('\n' if self.pretty else '').join(
                part for part in (stylesheet, content, runtime) if part
            )
            return _add_element_classes(html, self.profile.element_classes)
        title = (
            document.title
            if self.profile.include_metadata and document.title is not None
            else 'Report'
        )
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
        html = (
            '<!doctype html>'
            + ('\n' if self.pretty else '')
            + self._block('<html lang="en">', [head, body], '</html>', 0)
            + ('\n' if self.pretty else '')
        )
        return _add_element_classes(html, self.profile.element_classes)

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
        reader = self.toc_position == 'reader'
        sidebar = bool(navigation and self.toc_position in ('sidebar', 'reader'))
        article_depth = depth + int(sidebar)
        body = [
            self._render_node(node, outline, backlink, article_depth + 1)
            for node in document.children
        ]
        parts = []
        if self.profile.include_metadata:
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
        theme_attribute = (
            f' data-reporttkt-theme="{_style_id(self.style)}"'
            if self.profile.stylesheet == 'theme'
            else ' data-reporttkt-layout="minimal"'
        )
        content = self._block(
            f'<article class="reporttkt"{theme_attribute}>',
            parts,
            '</article>',
            article_depth,
        )
        if reader:
            title = (
                escape(document.title or 'Report')
                if self.profile.include_metadata
                else 'Report'
            )

            def control(name: str, label: str, icons: str, attributes: str = '') -> str:
                return (
                    f'<button class="{name}" type="button" aria-label="{label}"{attributes}>'
                    + icons
                    + f'<span class="report-reader-tooltip" role="tooltip" hidden>{label}</span>'
                    '</button>'
                )

            def icon(name: str, paths: str, *, hidden: bool = False) -> str:
                return (
                    f'<svg data-reader-icon="{name}" viewBox="0 0 24 24" '
                    'fill="none" stroke="currentColor" stroke-width="1.75" '
                    'stroke-linecap="round" stroke-linejoin="round" '
                    'aria-hidden="true" focusable="false"'
                    + (' hidden' if hidden else '')
                    + f'>{paths}</svg>'
                )

            toggle = (
                control(
                    'report-reader-toggle',
                    'Hide table of contents',
                    icon('menu', '<path d="M4 6h16M4 12h16M4 18h16"/>'),
                    ' aria-controls="reporttkt_sidebar" aria-expanded="true"',
                )
                if navigation
                else ''
            )
            theme = control(
                'report-theme-toggle',
                'Switch to dark mode',
                icon('moon', '<path d="M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z"/>')
                + icon(
                    'sun',
                    '<circle cx="12" cy="12" r="4"/>'
                    '<path d="M12 2v2m0 16v2M2 12h2m16 0h2'
                    'M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42'
                    'M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/>',
                    hidden=True,
                ),
            )
            width = control(
                'report-width-toggle',
                'Content width: Standard. Switch to Wide.',
                ''.join(
                    icon(
                        f'width-{mode}',
                        f'<path d="M{left} 4v16M{right} 4v16"/>'
                        f'<path d="M{left + 3} 8h{right - left - 6}'
                        f'M{left + 3} 12h{right - left - 6}'
                        f'M{left + 3} 16h{right - left - 6}"/>',
                        hidden=mode != 'standard',
                    )
                    for mode, left, right in (
                        ('standard', 4, 20),
                        ('wide', 2, 22),
                    )
                ),
            )
            bar = (
                '<div class="report-reader-bar"><div class="report-reader-bar-inner">'
                + toggle
                + f'<div class="report-reader-label"><div class="report-reader-title">{title}</div>'
                '<nav class="report-breadcrumbs" aria-label="Section breadcrumbs"></nav></div>'
                + width
                + theme
                + '</div></div>'
            )
            header_controls = control(
                'report-reader-close',
                'Close table of contents',
                icon('close', '<path d="m6 6 12 12M6 18 18 6"/>'),
            )
            if 'class="report-toc-toggle"' in navigation:
                header_controls += control(
                    'report-reader-collapse',
                    'Collapse all sections',
                    icon('collapse', '<path d="m7 9 5-5 5 5M7 15l5 5 5-5"/>'),
                )
            navigation = navigation.replace('<!--reader-controls-->', header_controls)
            side = (
                '<div class="report-sidebar" id="reporttkt_sidebar">'
                + navigation
                + '</div>'
                if navigation
                else ''
            )
            return self._block(
                f'<div class="reporttkt report-layout report-reader"{theme_attribute} '
                f'data-reader-mode="{self.style.mode}">',
                [bar, '<div class="report-reader-backdrop"></div>', side, content],
                '</div>',
                depth,
            )
        if sidebar:
            return self._block(
                f'<div class="reporttkt report-layout"{theme_attribute}>',
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

    @property
    def _navigation_enabled(self) -> bool:
        return (
            self.profile.stylesheet == 'theme'
            and self.profile.chart_mode == 'interactive'
        )

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
            button = (
                '<button class="report-toc-toggle" type="button" aria-expanded="true" '
                f'aria-label="Collapse {escape(label, quote=True)}" hidden="hidden">'
                + (
                    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    'stroke-width="1.75" aria-hidden="true" focusable="false">'
                    '<path d="m6 9 6 6 6-6"/></svg></button>'
                    if self.toc_position == 'reader'
                    else '<span aria-hidden="true">⌄</span></button>'
                )
                if self._navigation_enabled and self.collapsible_toc
                else ''
            )
            link = f'<a href="#{anchor}">{escape(label)}</a>'
            # Retain direct-child links for depth-based typography.
            stack[-1][1].append((link, button, children))
            stack.append((level, children))
        if not entries:
            return ''

        def render_entries(items: list[_TOCEntry], depth: int = 0) -> str:
            return (
                '<ul>'
                + ''.join(
                    (
                        '<li style="--reporttkt-toc-indent: '
                        + f'{min(depth, 2) * 0.75:g}rem">'
                        if self.toc_position == 'reader'
                        else '<li>'
                    )
                    + link
                    + (button if children else '')
                    + (render_entries(children, depth + 1) if children else '')
                    + '</li>'
                    for link, button, children in items
                )
                + '</ul>'
            )

        title = (
            '<div class="report-toc-title">Table of contents</div>'
            if self.profile.include_toc_title
            else ''
        )
        if self.toc_position == 'reader':
            title = (
                '<div class="report-reader-toc-header">'
                + title
                + '<!--reader-controls--></div>'
            )
        attributes = (
            f' data-reporttkt-navigation="{str(self.collapsible_toc).lower()}"'
            if self._navigation_enabled
            else ''
        )
        return (
            '<nav'
            + attributes
            + ' class="report-toc" id="reporttkt_toc" tabindex="-1" aria-label="Table of contents">'
            + title
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
            adapter = self.registry.resolve(node.value)
            render_for_profile = getattr(adapter, 'render_for_profile', None)
            if callable(render_for_profile):
                rendered = render_for_profile(node.value, profile=self.profile)
            elif self.profile.chart_mode == 'interactive':
                rendered = adapter.render(node.value)
            else:
                raise TypeError(
                    f'{type(adapter).__name__} must provide render_for_profile(value, *, profile) to support SVG profiles'
                )
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
                    f'<h{heading} id="{anchor}" data-reporttkt-heading="{heading}">{escape(label)}{backlink}</h{heading}>',
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

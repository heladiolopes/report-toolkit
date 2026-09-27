"""Composable HTML styles. CSS and token values are trusted author-provided code."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

_THEME_DEFAULTS = {
    'font_family': 'Roboto, "Noto Sans", sans-serif',
    'code_font': '"JetBrains Mono", "SFMono-Regular", "Consolas", "Liberation '
    'Mono", monospace',
    'font_size': '16px',
    'line_height': '1.5',
    'content_width': '1040px',
    'page_margin': '32px auto',
    'content_padding': '48px clamp(20px, 5vw, 72px)',
    'radius': '5px',
    'h1_size': '2em',
    'h2_size': '1.5em',
    'h3_size': '1.17em',
    'h4_size': '1em',
    'h5_size': '.83em',
    'h6_size': '.67em',
    'section_spacing': '2rem',
    'column_gap': '1.5rem',
    'caption_size': '.875rem',
    'table_size': '1em',
    'cell_padding': '.25rem .75rem',
    'figure_margin': '1.5rem 0',
    'panel_padding': '0',
    'shadow_geometry': '0 18px 42px',
    'title_size': '2.5rem',
    'heading_line_height': '1.2',
    'heading_margin': '1.5em 0 .5em',
    'h2_border_width': '0',
    'h2_padding': '0',
    'paragraph_margin': '0 0 .75rem',
    'list_margin': '0 0 .75rem',
    'list_item_spacing': '.25rem',
    'nested_list_margin': '0 0 .75rem',
    'link_decoration': 'none',
    'table_border_width': '1px',
    'table_line_height': '1.25',
    'pre_padding': '0',
    'pre_radius': '0',
    'pre_margin': '0 0 .75rem',
    'code_size': '1em',
    'blockquote_margin': '0 40px .75rem',
    'blockquote_padding': '0',
    'blockquote_border_width': '0',
    'toc_font_family': 'var(--reportkit-font-family)',
    'toc_line_height': 'var(--reportkit-line-height)',
    'title_weight': 'bold',
    'title_line_height': 'var(--reportkit-heading-line-height)',
    'caption_line_height': 'inherit',
    'code_line_height': 'inherit',
    'h1_weight': 'bold',
    'h1_line_height': 'var(--reportkit-heading-line-height)',
    'h2_weight': 'bold',
    'h2_line_height': 'var(--reportkit-heading-line-height)',
    'h3_weight': 'bold',
    'h3_line_height': 'var(--reportkit-heading-line-height)',
    'h4_weight': 'bold',
    'h4_line_height': 'var(--reportkit-heading-line-height)',
    'h5_weight': 'bold',
    'h5_line_height': 'var(--reportkit-heading-line-height)',
    'h6_weight': 'bold',
    'h6_line_height': 'var(--reportkit-heading-line-height)',
}

_SLATE_LIGHT = {
    'page_background': '#f5f5f5',
    'background': '#ffffff',
    'surface': '#f3f3f3',
    'text': '#262626',
    'heading': '#0a0a0a',
    'accent': '#2563eb',
    'description': '#6b6b6b',
    'muted': '#6b6b6b',
    'border': '#dddddd',
    'table_header': '#f5f5f5',
    'shadow_color': '#00000014',
    'panel_background': 'transparent',
    'accent_hover': '#1d4ed8',
    'pre_background': 'transparent',
    'blockquote_background': 'transparent',
    'toc_text': 'var(--reportkit-text)',
    'toc_background': 'var(--reportkit-surface)',
    'toc_accent': 'var(--reportkit-accent)',
}

_SLATE_DARK = {
    'page_background': '#111418',
    'background': '#1a1f24',
    'surface': '#22282f',
    'text': '#f2f4f5',
    'heading': '#f2f4f5',
    'accent': '#4d8cf5',
    'description': '#a9b0b7',
    'muted': '#a9b0b7',
    'border': '#30363d',
    'table_header': '#22282f',
    'shadow_color': '#00000099',
    'panel_background': 'transparent',
    'accent_hover': '#93c5fd',
    'pre_background': 'transparent',
    'blockquote_background': 'transparent',
    'toc_text': 'var(--reportkit-text)',
    'toc_background': 'var(--reportkit-surface)',
    'toc_accent': 'var(--reportkit-accent)',
}


def _name(value: str, kind: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f'{kind} name must be a string')
    if not value.strip():
        raise ValueError(f'{kind} name must not be empty')


def _tokens(
    values: Mapping[str, str], defaults: Mapping[str, str], kind: str
) -> dict[str, str]:
    if not isinstance(values, Mapping):
        raise TypeError(f'{kind} tokens must be a mapping')
    result = dict(values)
    for key, value in result.items():
        if key not in defaults:
            raise ValueError(f'Unknown {kind} token: {key!r}')
        if not isinstance(value, str):
            raise TypeError(f'{kind} token {key!r} must be a string')
        if not value.strip():
            raise ValueError(f'{kind} token {key!r} must not be empty')
    return result


@dataclass(frozen=True, kw_only=True)
class Theme:
    """Immutable structural presentation, inheriting the default theme.

    ``css`` is trusted CSS; ``&`` is replaced by the report root selector.
    Colors belong in a Palette rather than the theme token mapping.
    """

    name: str
    tokens: Mapping[str, str] = field(default_factory=dict)
    css: str = ''

    def __post_init__(self) -> None:
        _name(self.name, 'theme')
        if not isinstance(self.css, str):
            raise TypeError('theme css must be a string')
        object.__setattr__(
            self,
            'tokens',
            MappingProxyType(
                _THEME_DEFAULTS | _tokens(self.tokens, _THEME_DEFAULTS, 'theme')
            ),
        )

    def with_overrides(
        self,
        *,
        name: str,
        tokens: Mapping[str, str] | None = None,
        css: str | None = None,
    ) -> Theme:
        """Merge structural tokens, inheriting CSS unless a replacement is supplied."""
        return Theme(
            name=name,
            tokens=dict(self.tokens)
            | (_tokens(tokens, _THEME_DEFAULTS, 'theme') if tokens is not None else {}),
            css=self.css if css is None else css,
        )


@dataclass(frozen=True, kw_only=True)
class Palette:
    """Immutable light/dark colors; omitted tokens inherit the matching slate mode."""

    name: str
    light: Mapping[str, str] = field(default_factory=dict)
    dark: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _name(self.name, 'palette')
        for mode, defaults in (('light', _SLATE_LIGHT), ('dark', _SLATE_DARK)):
            object.__setattr__(
                self,
                mode,
                MappingProxyType(
                    defaults | _tokens(getattr(self, mode), defaults, 'palette')
                ),
            )

    def with_overrides(
        self,
        *,
        name: str,
        light: Mapping[str, str] | None = None,
        dark: Mapping[str, str] | None = None,
    ) -> Palette:
        """Merge each supplied color mapping and inherit the other mode."""
        return Palette(
            name=name,
            light=dict(self.light)
            | (_tokens(light, _SLATE_LIGHT, 'palette') if light is not None else {}),
            dark=dict(self.dark)
            | (_tokens(dark, _SLATE_DARK, 'palette') if dark is not None else {}),
        )


@dataclass(frozen=True, kw_only=True)
class Style:
    """Writer presentation: a structural theme, a color palette, and a display mode."""

    theme: str | Theme = 'default'
    palette: str | Palette = 'slate'
    mode: Literal['light', 'dark', 'auto'] = 'light'

    def __post_init__(self) -> None:
        if isinstance(self.theme, str):
            get_theme(self.theme)
        elif not isinstance(self.theme, Theme):
            raise TypeError('style theme must be a name or Theme')
        if isinstance(self.palette, str):
            get_palette(self.palette)
        elif not isinstance(self.palette, Palette):
            raise TypeError('style palette must be a name or Palette')
        if not isinstance(self.mode, str):
            raise TypeError('style mode must be a string')
        if self.mode not in ('light', 'dark', 'auto'):
            raise ValueError("style mode must be 'light', 'dark', or 'auto'")


_THEMES = {'default': Theme(name='default')}
_PALETTES = {
    'slate': Palette(name='slate'),
    'azure': Palette(
        name='azure',
        light={
            'accent': '#0067f6',
            'accent_hover': '#0958d9',
            'border': '#d9d9d9',
            'description': '#595959',
            'heading': '#262626',
            'muted': '#595959',
            'surface': '#f5f5f5',
        },
        dark={
            'accent': '#60a5fa',
            'background': '#1f1f1f',
            'border': '#424242',
            'description': '#a3a3a3',
            'heading': '#e5e5e5',
            'muted': '#a3a3a3',
            'page_background': '#141414',
            'surface': '#262626',
            'table_header': '#262626',
            'text': '#e5e5e5',
        },
    ),
    'parchment': Palette(
        name='parchment',
        light={
            'accent': '#316ac6',
            'accent_hover': '#3565a6',
            'background': '#fcfcf9',
            'border': '#d7d7d6',
            'description': '#666666',
            'heading': '#181818',
            'muted': '#666666',
            'page_background': '#efefe4',
            'surface': '#f3f3f4',
            'table_header': '#f3f3f4',
            'text': '#181818',
        },
        dark={
            'accent': '#5893f6',
            'background': '#252320',
            'border': '#51493e',
            'description': '#d0c5b4',
            'heading': '#e8e1d5',
            'muted': '#d0c5b4',
            'page_background': '#191817',
            'surface': '#302d28',
            'table_header': '#302d28',
            'text': '#e8e1d5',
        },
    ),
    'ember': Palette(
        name='ember',
        light={
            'accent': '#be4e29',
            'accent_hover': '#a74729',
            'border': '#dedbd3',
            'description': '#6b6963',
            'heading': '#252525',
            'muted': '#6b6963',
            'page_background': '#f7f6f2',
            'surface': '#f7f6f2',
            'table_header': '#f7f6f2',
            'text': '#252525',
        },
        dark={
            'accent': '#da7756',
            'accent_hover': '#f0a080',
            'background': '#24221f',
            'border': '#413d37',
            'description': '#aaa49a',
            'heading': '#eeeae3',
            'muted': '#aaa49a',
            'page_background': '#1a1917',
            'surface': '#2d2a26',
            'table_header': '#2d2a26',
            'text': '#eeeae3',
        },
    ),
}


def get_theme(name: str) -> Theme:
    """Return a structural theme by name (currently only ``default``)."""
    _name(name, 'theme')
    try:
        return _THEMES[name]
    except KeyError:
        raise ValueError(
            f'Unknown theme {name!r}; choose from {", ".join(_THEMES)}'
        ) from None


def get_palette(name: str) -> Palette:
    """Return one of the slate, azure, parchment, or ember color palettes."""
    _name(name, 'palette')
    try:
        return _PALETTES[name]
    except KeyError:
        raise ValueError(
            f'Unknown palette {name!r}; choose from {", ".join(_PALETTES)}'
        ) from None


def _resolve_style(style: Style | Mapping[str, object] | None) -> Style:
    if style is None:
        style = Style()
    elif isinstance(style, Mapping):
        unknown = style.keys() - {'theme', 'palette', 'mode'}
        if unknown:
            raise ValueError(
                f'Unknown style fields: {", ".join(sorted(map(repr, unknown)))}'
            )
        style = Style(**style)
    elif not isinstance(style, Style):
        raise TypeError('style must be a Style, mapping, or None')
    return Style(
        theme=get_theme(style.theme) if isinstance(style.theme, str) else style.theme,
        palette=get_palette(style.palette)
        if isinstance(style.palette, str)
        else style.palette,
        mode=style.mode,
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
    base = re.sub(r'\.reportkit(?![\w-])', lambda match: selector, _CSS)

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


_CSS = """
.reportkit, .reportkit * { box-sizing: border-box; }
.reportkit { max-width: var(--reportkit-content-width); margin: var(--reportkit-page-margin); padding: var(--reportkit-content-padding); background: var(--reportkit-background); border: 1px solid var(--reportkit-border); border-radius: var(--reportkit-radius); box-shadow: var(--reportkit-shadow-geometry) var(--reportkit-shadow-color); }
.reportkit { color: var(--reportkit-text); font: var(--reportkit-font-size)/var(--reportkit-line-height) var(--reportkit-font-family); }
.reportkit h1, .reportkit h2, .reportkit h3, .reportkit h4, .reportkit h5, .reportkit h6 { color: var(--reportkit-heading); line-height: var(--reportkit-heading-line-height); margin: var(--reportkit-heading-margin); }
.reportkit h1 { font-size: var(--reportkit-h1-size); font-weight: var(--reportkit-h1-weight); line-height: var(--reportkit-h1-line-height); margin-top: 0; }
.reportkit .report-title { font-size: var(--reportkit-title-size); font-weight: var(--reportkit-title-weight); line-height: var(--reportkit-title-line-height); margin: 0 0 .5em; }
.reportkit h2 { font-size: var(--reportkit-h2-size); font-weight: var(--reportkit-h2-weight); line-height: var(--reportkit-h2-line-height); border-bottom: var(--reportkit-h2-border-width) solid var(--reportkit-border); padding-bottom: var(--reportkit-h2-padding); }
.reportkit p { margin: var(--reportkit-paragraph-margin); }
.reportkit ul, .reportkit ol { margin: var(--reportkit-list-margin); }
.reportkit ul ul, .reportkit ul ol, .reportkit ol ul, .reportkit ol ol { margin: var(--reportkit-nested-list-margin); }
.reportkit li + li { margin-top: var(--reportkit-list-item-spacing); }
.reportkit a { color: var(--reportkit-accent); text-decoration: var(--reportkit-link-decoration); }
.reportkit a:hover { color: var(--reportkit-accent-hover); text-decoration: underline; }
.reportkit .report-description { color: var(--reportkit-description); font-size: 1.1rem; }
.reportkit .report-meta { color: var(--reportkit-muted); font-size: var(--reportkit-caption-size); line-height: var(--reportkit-caption-line-height); display: flex; flex-wrap: wrap; gap: 1.2rem; }
.reportkit .report-section { margin-top: var(--reportkit-section-spacing); }
.reportkit .report-columns { display: grid; grid-template-columns: repeat(var(--reportkit-columns), minmax(0, 1fr)); gap: var(--reportkit-column-gap); align-items: start; }
.reportkit .report-column-item { min-width: 0; }
.reportkit .report-panel { min-width: 0; overflow-x: auto; background: var(--reportkit-panel-background); padding: var(--reportkit-panel-padding); }
.reportkit .report-panel-title { color: var(--reportkit-heading); font-weight: 650; margin-bottom: .75rem; }
.reportkit .report-toc { margin: 1.5rem 0; padding: 1rem 1.5rem; background: var(--reportkit-toc-background); border-radius: var(--reportkit-radius); color: var(--reportkit-toc-text); font-family: var(--reportkit-toc-font-family); line-height: var(--reportkit-toc-line-height); }
.reportkit .report-toc a { color: var(--reportkit-toc-accent); text-decoration: none; }
.reportkit .report-toc a:hover, .reportkit .report-toc a:focus-visible { color: var(--reportkit-accent-hover); text-decoration: underline; }
.reportkit .report-toc a:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; border-radius: 2px; }
.reportkit .report-toc li + li { margin-top: 0; }
.reportkit .report-toc-title { font-weight: var(--reportkit-h4-weight); }
.reportkit .report-toc ul { padding-left: 1.5rem; margin: revert; }
.reportkit .report-artifact { margin: var(--reportkit-figure-margin); min-width: 0; overflow-x: auto; }
.reportkit figcaption { color: var(--reportkit-muted); font-size: var(--reportkit-caption-size); line-height: var(--reportkit-caption-line-height); margin-top: .5rem; }
.reportkit .reportkit-figure-image { display: block; max-width: 100%; height: auto; }
.reportkit table { border-collapse: collapse; width: 100%; font-size: var(--reportkit-table-size); line-height: var(--reportkit-table-line-height); }
.reportkit th, .reportkit td { border: var(--reportkit-table-border-width) solid var(--reportkit-border); border-bottom: 1px solid var(--reportkit-border); padding: var(--reportkit-cell-padding); text-align: left; }
.reportkit th { background: var(--reportkit-table-header); font-weight: 650; }
.reportkit pre { line-height: var(--reportkit-code-line-height); overflow-x: auto; padding: var(--reportkit-pre-padding); background: var(--reportkit-pre-background); border-radius: var(--reportkit-pre-radius); margin: var(--reportkit-pre-margin); }
.reportkit code { font-size: var(--reportkit-code-size); font-family: var(--reportkit-code-font); line-height: var(--reportkit-code-line-height); }
.reportkit h3 { font-size: var(--reportkit-h3-size); font-weight: var(--reportkit-h3-weight); line-height: var(--reportkit-h3-line-height); }
.reportkit h4 { font-size: var(--reportkit-h4-size); font-weight: var(--reportkit-h4-weight); line-height: var(--reportkit-h4-line-height); }
.reportkit h5 { font-size: var(--reportkit-h5-size); font-weight: var(--reportkit-h5-weight); line-height: var(--reportkit-h5-line-height); }
.reportkit h6 { font-size: var(--reportkit-h6-size); font-weight: var(--reportkit-h6-weight); line-height: var(--reportkit-h6-line-height); }
.reportkit blockquote { margin: var(--reportkit-blockquote-margin); padding: var(--reportkit-blockquote-padding); border-left: var(--reportkit-blockquote-border-width) solid var(--reportkit-accent); background: var(--reportkit-blockquote-background); }
.reportkit hr { border: 0; border-top: 1px solid var(--reportkit-border); }
.reportkit .report-toc-backlink { font-size: .7em; white-space: nowrap; }
.reportkit .report-toc a { overflow-wrap: anywhere; }
.reportkit.report-layout { display: grid; grid-template-columns: 16rem minmax(0, 1fr); gap: 1.5rem; align-items: start; max-width: calc(var(--reportkit-content-width) + 17.5rem); padding: 0; background: transparent; border: 0; border-radius: 0; box-shadow: none; }
.reportkit.report-layout > article.reportkit { min-width: 0; width: 100%; margin: 0; }
.reportkit .report-sidebar { position: sticky; top: 1rem; min-width: 0; }
.reportkit .report-sidebar .report-toc { margin: 0; max-height: calc(100vh - 2rem); overflow-y: auto; overscroll-behavior: contain; }
@media (max-width: 1099px) {
    .reportkit.report-layout { grid-template-columns: minmax(0, 1fr); max-width: var(--reportkit-content-width); }
    .reportkit .report-sidebar { position: static; }
    .reportkit .report-sidebar .report-toc { max-height: none; overflow: visible; }
}
@media print {
    .reportkit.report-layout { display: block; max-width: none; }
    .reportkit .report-sidebar { position: static; }
    .reportkit .report-sidebar .report-toc { max-height: none; overflow: visible; }
    .reportkit .report-toc-backlink { display: none; }
}

@media (max-width: 700px) { .reportkit { margin: 0; border: 0; border-radius: 0; padding: 24px 18px; } .reportkit .report-columns { grid-template-columns: 1fr; } }
""".strip()

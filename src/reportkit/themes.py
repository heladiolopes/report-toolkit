"""Reusable HTML themes. CSS and token values are trusted author-provided code."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

_DEFAULT_TOKENS = {
    'page_background': '#f4f6fa',
    'background': '#ffffff',
    'surface': '#f4f6fa',
    'text': '#1d2939',
    'heading': '#14233b',
    'accent': '#1259a8',
    'description': '#52637a',
    'muted': '#617189',
    'border': '#e5eaf0',
    'table_header': '#f7f9fc',
    'shadow_color': '#1d29390c',
    'font_family': 'system-ui, sans-serif',
    'code_font': 'ui-monospace, monospace',
    'font_size': '16px',
    'line_height': '1.65',
    'content_width': '1040px',
    'page_margin': '32px auto',
    'content_padding': '48px clamp(20px, 5vw, 72px)',
    'radius': '12px',
    'h1_size': '2.25rem',
    'h2_size': '1.65rem',
    'h3_size': '1.17em',
    'h4_size': '1em',
    'h5_size': '.83em',
    'h6_size': '.67em',
    'section_spacing': '2rem',
    'column_gap': '1.5rem',
    'caption_size': '.875rem',
    'table_size': '.9rem',
    'cell_padding': '.55rem .75rem',
    'figure_margin': '1.5rem 0',
    'panel_background': 'transparent',
    'panel_padding': '0',
}


def _tokens(values: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(values, Mapping):
        raise TypeError('theme tokens must be a mapping')
    result = dict(values)
    for key, value in result.items():
        if key not in _DEFAULT_TOKENS:
            raise ValueError(f'Unknown theme token: {key!r}')
        if not isinstance(value, str):
            raise TypeError(f'Theme token {key!r} must be a string')
        if not value.strip():
            raise ValueError(f'Theme token {key!r} must not be empty')
    return result


@dataclass(frozen=True, kw_only=True)
class Theme:
    """An immutable theme; omitted tokens inherit the default light styling.

    Use ``get_theme('dark').with_overrides(...)`` to inherit dark styling.
    ``css`` is trusted CSS, with ``&`` replaced by the report root selector.
    """

    name: str
    mode: Literal['light', 'dark'] = 'light'
    tokens: Mapping[str, str] = field(default_factory=dict)
    css: str = ''

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError('theme name must be a string')
        if not self.name.strip():
            raise ValueError('theme name must not be empty')
        if self.mode not in ('light', 'dark'):
            raise ValueError("theme mode must be 'light' or 'dark'")
        if not isinstance(self.css, str):
            raise TypeError('theme css must be a string')
        object.__setattr__(
            self, 'tokens', MappingProxyType(_DEFAULT_TOKENS | _tokens(self.tokens))
        )

    def with_overrides(
        self,
        *,
        name: str,
        tokens: Mapping[str, str] | None = None,
        css: str | None = None,
    ) -> Theme:
        """Derive a theme, merging tokens and replacing CSS when supplied."""
        return Theme(
            name=name,
            mode=self.mode,
            tokens=dict(self.tokens) | (_tokens(tokens) if tokens is not None else {}),
            css=self.css if css is None else css,
        )


@dataclass(frozen=True, kw_only=True)
class AutoTheme:
    """Select a light or dark theme using the reader's system preference."""

    light: Theme
    dark: Theme

    def __post_init__(self) -> None:
        for mode in ('light', 'dark'):
            theme = getattr(self, mode)
            if not isinstance(theme, Theme):
                raise TypeError(f'{mode} must be a Theme')
            if theme.mode != mode:
                raise ValueError(f'{mode} theme must have mode={mode!r}')


_LIGHT = Theme(name='light')
_DARK = Theme(
    name='dark',
    mode='dark',
    tokens={
        'page_background': '#101722',
        'background': '#182231',
        'surface': '#202e40',
        'text': '#e0e7ef',
        'heading': '#f1f5fa',
        'accent': '#91baff',
        'description': '#bac9dc',
        'muted': '#a8b9ce',
        'border': '#3b4c62',
        'table_header': '#26364b',
        'shadow_color': '#00000033',
    },
)
_PAPER = Theme(
    name='paper',
    tokens={
        'page_background': '#eee9de',
        'background': '#fffcf5',
        'surface': '#f2ecdf',
        'text': '#38352e',
        'heading': '#30291f',
        'accent': '#795020',
        'description': '#655d50',
        'muted': '#6d6252',
        'border': '#d9cfbe',
        'table_header': '#f2ecdf',
        'font_family': 'Georgia, serif',
        'shadow_color': '#30291f0c',
    },
)
_INK = Theme(
    name='ink',
    mode='dark',
    tokens={
        'page_background': '#191817',
        'background': '#252320',
        'surface': '#302d28',
        'text': '#e8e1d5',
        'heading': '#fff6e8',
        'accent': '#e8bd80',
        'description': '#d0c5b4',
        'muted': '#bfb3a0',
        'border': '#51493e',
        'table_header': '#373229',
        'font_family': 'Georgia, serif',
        'shadow_color': '#00000033',
    },
)
_PRESETS = {theme.name: theme for theme in (_LIGHT, _DARK, _PAPER, _INK)} | {
    'auto': AutoTheme(light=_LIGHT, dark=_DARK),
    'auto-paper': AutoTheme(light=_PAPER, dark=_INK),
}


def get_theme(name: str) -> Theme | AutoTheme:
    """Return light, dark, paper, ink, auto, or auto-paper."""
    if not isinstance(name, str):
        raise TypeError('theme name must be a string')
    try:
        return _PRESETS[name]
    except KeyError:
        raise ValueError(
            f'Unknown theme {name!r}; choose from {", ".join(_PRESETS)}'
        ) from None


def _resolve_theme(theme: str | Theme | AutoTheme) -> Theme | AutoTheme:
    if isinstance(theme, str):
        return get_theme(theme)
    if not isinstance(theme, (Theme, AutoTheme)):
        raise TypeError('theme must be a preset name, Theme, or AutoTheme')
    return theme


def _theme_id(theme: Theme | AutoTheme) -> str:
    # Content-derived scopes distinguish custom themes even if names are reused.
    themes = (theme.light, theme.dark) if isinstance(theme, AutoTheme) else (theme,)
    payload = [(t.name, t.mode, dict(t.tokens), t.css) for t in themes]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def _stylesheet(theme: Theme | AutoTheme, *, fragment: bool) -> str:
    # :where keeps specificity low enough for Pandas Styler's explicit rules.
    selector = f'.reportkit:where([data-reportkit-theme="{_theme_id(theme)}"])'
    base = re.sub(r'\.reportkit(?![\w-])', lambda match: selector, _CSS)

    def variables(selected: Theme) -> str:
        declarations = '\n'.join(
            f'  --reportkit-{key.replace("_", "-")}: {value};'
            for key, value in selected.tokens.items()
        )
        rules = f'{selector} {{\n{declarations}\n  color-scheme: {selected.mode};\n}}'
        if not fragment:
            rules += (
                '\nbody { margin: 0; background: '
                + selected.tokens['page_background']
                + f'; color-scheme: {selected.mode}; }}'
            )
        return rules

    def extra(selected: Theme) -> str:
        return selected.css.replace('&', selector)

    if isinstance(theme, AutoTheme):
        css = variables(theme.light) + '\n' + base
        # Keep light-only overrides out of dark mode, even when the dark theme
        # does not override the same properties.
        if theme.light.css:
            css += (
                '\n@media not all and (prefers-color-scheme: dark) {\n'
                + extra(theme.light)
                + '\n}'
            )
        css += (
            '\n@media (prefers-color-scheme: dark) {\n'
            + variables(theme.dark)
            + '\n'
            + extra(theme.dark)
            + '\n}'
        )
    else:
        css = variables(theme) + '\n' + base + '\n' + extra(theme)
    # Prevent a CSS string from terminating the surrounding HTML style element.
    return css.replace('<', r'\3c ')


_CSS = """
.reportkit, .reportkit * { box-sizing: border-box; }
.reportkit { max-width: var(--reportkit-content-width); margin: var(--reportkit-page-margin); padding: var(--reportkit-content-padding); background: var(--reportkit-background); border: 1px solid var(--reportkit-border); border-radius: var(--reportkit-radius); box-shadow: 0 12px 36px var(--reportkit-shadow-color); }
.reportkit { color: var(--reportkit-text); font: var(--reportkit-font-size)/var(--reportkit-line-height) var(--reportkit-font-family); }
.reportkit h1, .reportkit h2, .reportkit h3, .reportkit h4, .reportkit h5, .reportkit h6 { color: var(--reportkit-heading); line-height: 1.25; margin: 1.7em 0 .55em; }
.reportkit h1 { font-size: var(--reportkit-h1-size); margin-top: 0; }
.reportkit .report-title { font-size: clamp(var(--reportkit-h1-size), 5vw, 3rem); margin: 0 0 .5em; }
.reportkit h2 { font-size: var(--reportkit-h2-size); border-bottom: 1px solid var(--reportkit-border); padding-bottom: .25em; }
.reportkit p { margin: .6em 0 1.1em; }
.reportkit a { color: var(--reportkit-accent); }
.reportkit .report-description { color: var(--reportkit-description); font-size: 1.1rem; }
.reportkit .report-meta { color: var(--reportkit-muted); font-size: var(--reportkit-caption-size); display: flex; flex-wrap: wrap; gap: 1.2rem; }
.reportkit .report-section { margin-top: var(--reportkit-section-spacing); }
.reportkit .report-columns { display: grid; grid-template-columns: repeat(var(--reportkit-columns), minmax(0, 1fr)); gap: var(--reportkit-column-gap); align-items: start; }
.reportkit .report-column-item { min-width: 0; }
.reportkit .report-panel { min-width: 0; overflow-x: auto; background: var(--reportkit-panel-background); padding: var(--reportkit-panel-padding); }
.reportkit .report-panel-title { color: var(--reportkit-heading); font-weight: 650; margin-bottom: .75rem; }
.reportkit .report-toc { margin: 1.5rem 0; padding: 1rem 1.5rem; background: var(--reportkit-surface); border-radius: 6px; }
.reportkit .report-toc-title { font-weight: 650; }
.reportkit .report-toc ul { padding-left: 1.5rem; }
.reportkit .report-artifact { margin: var(--reportkit-figure-margin); min-width: 0; overflow-x: auto; }
.reportkit figcaption { color: var(--reportkit-muted); font-size: var(--reportkit-caption-size); margin-top: .5rem; }
.reportkit .reportkit-figure-image { display: block; max-width: 100%; height: auto; }
.reportkit table { border-collapse: collapse; width: 100%; font-size: var(--reportkit-table-size); }
.reportkit th, .reportkit td { border-bottom: 1px solid var(--reportkit-border); padding: var(--reportkit-cell-padding); text-align: left; }
.reportkit th { background: var(--reportkit-table-header); font-weight: 650; }
.reportkit pre { overflow-x: auto; padding: 1rem; background: var(--reportkit-surface); border-radius: 6px; }
.reportkit code { font-size: .9em; font-family: var(--reportkit-code-font); }
.reportkit h3 { font-size: var(--reportkit-h3-size); }
.reportkit h4 { font-size: var(--reportkit-h4-size); }
.reportkit h5 { font-size: var(--reportkit-h5-size); }
.reportkit h6 { font-size: var(--reportkit-h6-size); }
.reportkit blockquote { margin: 1rem 0; padding: .25rem 1rem; border-left: 3px solid var(--reportkit-accent); background: var(--reportkit-surface); }
.reportkit hr { border: 0; border-top: 1px solid var(--reportkit-border); }
@media (max-width: 700px) { .reportkit { margin: 0; border: 0; border-radius: 0; padding: 24px 18px; } .reportkit .report-columns { grid-template-columns: 1fr; } }
""".strip()

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
    'font_family': 'Roboto, "Noto Sans", sans-serif',
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


# Keep the alternative presets' presentation independent of default restyling.
_DEFAULT_TOKENS.update(
    {
        'shadow_geometry': '0 12px 36px',
        'title_size': 'clamp(var(--reportkit-h1-size), 5vw, 3rem)',
        'heading_line_height': '1.25',
        'heading_margin': '1.7em 0 .55em',
        'h2_border_width': '1px',
        'h2_padding': '.25em',
        'paragraph_margin': '.6em 0 1.1em',
        'list_margin': 'revert',
        'list_item_spacing': '0',
        'nested_list_margin': 'revert',
        'link_decoration': 'underline',
        'accent_hover': 'var(--reportkit-heading)',
        'table_border_width': '0',
        'table_line_height': 'inherit',
        'pre_padding': '1rem',
        'pre_background': 'var(--reportkit-surface)',
        'pre_radius': '6px',
        'pre_margin': '1em 0',
        'code_size': '.9em',
        'blockquote_margin': '1rem 0',
        'blockquote_padding': '.25rem 1rem',
        'blockquote_border_width': '3px',
        'blockquote_background': 'var(--reportkit-surface)',
        'toc_font_family': 'var(--reportkit-font-family)',
        'toc_line_height': 'var(--reportkit-line-height)',
        'toc_text': 'var(--reportkit-text)',
        'toc_background': 'var(--reportkit-surface)',
        'toc_accent': 'var(--reportkit-accent)',
    }
)
_ALTERNATIVE_DEFAULTS = dict(_DEFAULT_TOKENS)
_DEFAULT_TOKENS.update(
    {
        'page_background': '#f5f5f5',
        'surface': '#f3f3f3',
        'text': '#262626',
        'heading': '#0a0a0a',
        'accent': '#2563eb',
        'accent_hover': '#1d4ed8',
        'description': '#6b6b6b',
        'muted': '#6b6b6b',
        'border': '#dddddd',
        'table_header': '#f5f5f5',
        'shadow_color': '#00000014',
        'shadow_geometry': '0 18px 42px',
        'font_family': 'Roboto, "Noto Sans", sans-serif',
        'code_font': '"JetBrains Mono", "SFMono-Regular", "Consolas", "Liberation Mono", monospace',
        'line_height': '1.5',
        'radius': '5px',
        'h1_size': '2em',
        'h2_size': '1.5em',
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
        'table_size': '1em',
        'cell_padding': '.25rem .75rem',
        'table_border_width': '1px',
        'table_line_height': '1.25',
        'pre_padding': '0',
        'pre_background': 'transparent',
        'pre_radius': '0',
        'pre_margin': '0 0 .75rem',
        'code_size': '1em',
        'blockquote_margin': '0 40px .75rem',
        'blockquote_padding': '0',
        'blockquote_border_width': '0',
        'blockquote_background': 'transparent',
    }
)


_DEFAULT_TOKENS.update(
    {
        'title_weight': 'bold',
        'title_line_height': 'var(--reportkit-heading-line-height)',
        'caption_line_height': 'inherit',
        'code_line_height': 'inherit',
    }
)
for _level in range(1, 7):
    _DEFAULT_TOKENS[f'h{_level}_weight'] = 'bold'
    _DEFAULT_TOKENS[f'h{_level}_line_height'] = 'var(--reportkit-heading-line-height)'


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
        'page_background': '#0a0a0a',
        'background': '#111111',
        'surface': '#171717',
        'text': '#e5e5e5',
        'heading': '#fafafa',
        'accent': '#60a5fa',
        'accent_hover': '#93c5fd',
        'description': '#a3a3a3',
        'muted': '#a3a3a3',
        'border': '#2a2a2a',
        'table_header': '#1a1a1a',
        'shadow_color': '#00000099',
        'shadow_geometry': '0 20px 48px',
    },
)
_PAPER = Theme(
    name='paper',
    tokens={
        **_ALTERNATIVE_DEFAULTS,
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
        'font_family': 'Roboto, "Noto Sans", sans-serif',
        'shadow_color': '#30291f0c',
    },
)
_INK = Theme(
    name='ink',
    mode='dark',
    tokens={
        **_ALTERNATIVE_DEFAULTS,
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
        'font_family': 'Roboto, "Noto Sans", sans-serif',
        'shadow_color': '#00000033',
    },
)
# Adapt Carbon's type scale to the existing report fonts and page layout.
_CARBON_TYPE = {
    'title_size': '2.625rem',
    'title_line_height': '3.125rem',
    'title_weight': '300',
    'h1_size': '2rem',
    'h1_line_height': '2.5rem',
    'h1_weight': '400',
    'h2_size': '1.75rem',
    'h2_line_height': '2.25rem',
    'h2_weight': '400',
    'h3_size': '1.25rem',
    'h3_line_height': '1.75rem',
    'h3_weight': '400',
    'h4_size': '1rem',
    'h4_line_height': '1.5rem',
    'h4_weight': '600',
    'h5_size': '.875rem',
    'h5_line_height': '1.25rem',
    'h5_weight': '600',
    'h6_size': '.875rem',
    'h6_line_height': '1.25rem',
    'h6_weight': '600',
    'font_size': '16px',
    'line_height': '1.5',
    'caption_size': '.875rem',
    'caption_line_height': '1.125rem',
    'code_size': '.875rem',
    'code_line_height': '1.25rem',
}
_CARBON = _LIGHT.with_overrides(
    name='carbon',
    tokens={
        **_CARBON_TYPE,
        'page_background': '#f4f4f4',
        'background': '#ffffff',
        'surface': '#f4f4f4',
        'text': '#161616',
        'heading': '#161616',
        'accent': '#0f62fe',
        'accent_hover': '#0043ce',
        'description': '#525252',
        'muted': '#525252',
        'border': '#e0e0e0',
        'table_header': '#f4f4f4',
    },
)
_CARBON_DARK = _DARK.with_overrides(
    name='carbon-dark',
    tokens={
        **_CARBON_TYPE,
        'page_background': '#0f0f0f',
        'background': '#161616',
        'surface': '#262626',
        'text': '#f4f4f4',
        'heading': '#f4f4f4',
        'accent': '#78a9ff',
        'accent_hover': '#a6c8ff',
        'description': '#c6c6c6',
        'muted': '#c6c6c6',
        'border': '#393939',
        'table_header': '#262626',
    },
)
_PRESETS = {
    theme.name: theme for theme in (_LIGHT, _DARK, _PAPER, _INK, _CARBON, _CARBON_DARK)
} | {
    'auto': AutoTheme(light=_LIGHT, dark=_DARK),
    'auto-paper': AutoTheme(light=_PAPER, dark=_INK),
    'auto-carbon': AutoTheme(light=_CARBON, dark=_CARBON_DARK),
}


def get_theme(name: str) -> Theme | AutoTheme:
    """Return a fixed theme or an automatic light/dark pair by preset name."""
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

"""Structural themes and built-in theme lookup."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from ._validation import _name, _tokens

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


@dataclass(frozen=True, kw_only=True)
class Theme:
    """Immutable structural presentation, inheriting the default theme.

    ``css`` is trusted CSS; ``&`` is replaced by the report root selector.
    Colors belong in a Palette rather than the theme token mapping.

    Parameters
    ----------
    name : str
        Theme name.
    tokens : mapping of str to str, optional
        Structural CSS tokens. Omitted tokens inherit the default theme values.
    css : str, optional
        Additional trusted CSS. The ampersand (``&``) is replaced by the
        report root selector.

    Raises
    ------
    TypeError
        If ``css`` is not a string or tokens are not string mappings.
    ValueError
        If the name or token keys/values are invalid.
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
        """Return a theme with selected structural token or CSS overrides.

        Parameters
        ----------
        name : str
            Name for the returned theme.
        tokens : mapping of str to str, optional
            Token values merged over this theme's tokens.
        css : str or None, optional
            Replacement CSS. If omitted or ``None``, this theme's CSS is kept.

        Returns
        -------
        Theme
            A new theme; this instance is unchanged.

        Raises
        ------
        TypeError
            If ``css`` or token values have unsupported types.
        ValueError
            If the name or tokens are invalid.
        """
        return Theme(
            name=name,
            tokens=dict(self.tokens)
            | (_tokens(tokens, _THEME_DEFAULTS, 'theme') if tokens is not None else {}),
            css=self.css if css is None else css,
        )


_THEMES = {'default': Theme(name='default')}


def get_theme(name: str) -> Theme:
    """Return a built-in structural theme by name.

    Parameters
    ----------
    name : str
        Built-in theme name. Currently only ``'default'`` is available.

    Returns
    -------
    Theme
        The requested theme.

    Raises
    ------
    TypeError
        If ``name`` is not a string.
    ValueError
        If the name is not recognized.
    """
    _name(name, 'theme')
    try:
        return _THEMES[name]
    except KeyError:
        raise ValueError(
            f'Unknown theme {name!r}; choose from {", ".join(_THEMES)}'
        ) from None

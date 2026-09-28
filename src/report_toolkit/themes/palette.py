"""Color palettes and built-in palette lookup."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from ._validation import _name, _tokens

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
    'toc_text': 'var(--reporttkt-text)',
    'toc_background': 'var(--reporttkt-surface)',
    'toc_accent': 'var(--reporttkt-accent)',
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
    'toc_text': 'var(--reporttkt-text)',
    'toc_background': 'var(--reporttkt-surface)',
    'toc_accent': 'var(--reporttkt-accent)',
}


@dataclass(frozen=True, kw_only=True)
class Palette:
    """Immutable light and dark colors for a report.

    Omitted color tokens inherit their values from the corresponding slate mode.

    Parameters
    ----------
    name : str
        Palette name.
    light, dark : mapping of str to str, optional
        Color tokens for light and dark display modes.

    Raises
    ------
    TypeError
        If a mapping key or value has an unsupported type.
    ValueError
        If the name or token keys/values are invalid.
    """

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
        """Return a palette with selected light or dark color overrides.

        Parameters
        ----------
        name : str
            Name for the returned palette.
        light, dark : mapping of str to str, optional
            Color tokens merged over the corresponding mapping in this palette.
            An omitted mapping is inherited unchanged.

        Returns
        -------
        Palette
            A new palette; this instance is unchanged.

        Raises
        ------
        TypeError
            If a mapping key or value has an unsupported type.
        ValueError
            If the name or tokens are invalid.
        """
        return Palette(
            name=name,
            light=dict(self.light)
            | (_tokens(light, _SLATE_LIGHT, 'palette') if light is not None else {}),
            dark=dict(self.dark)
            | (_tokens(dark, _SLATE_DARK, 'palette') if dark is not None else {}),
        )


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


def get_palette(name: str) -> Palette:
    """Return a built-in color palette by name.

    Parameters
    ----------
    name : str
        Palette name: ``'slate'``, ``'azure'``, ``'parchment'``, or ``'ember'``.

    Returns
    -------
    Palette
        The requested palette.

    Raises
    ------
    TypeError
        If ``name`` is not a string.
    ValueError
        If the name is not recognized.
    """
    _name(name, 'palette')
    try:
        return _PALETTES[name]
    except KeyError:
        raise ValueError(
            f'Unknown palette {name!r}; choose from {", ".join(_PALETTES)}'
        ) from None

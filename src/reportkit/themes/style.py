"""Style configuration and normalization."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from .palette import Palette, get_palette
from .theme import Theme, get_theme


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

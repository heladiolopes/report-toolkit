"""Immutable capabilities for HTML rendering environments."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Literal


@dataclass(frozen=True, kw_only=True)
class RenderingProfile:
    """HTML capabilities and additive element classes, independent of themes.

    ``element_classes`` maps lowercase HTML tags to tuples of class tokens.
    Custom adapters must explicitly support profiles requesting SVG charts.
    """

    name: str
    chart_mode: Literal['interactive', 'svg'] = 'interactive'
    content_only: bool = False
    include_metadata: bool = True
    include_toc_title: bool = True
    stylesheet: Literal['theme', 'layout'] = 'theme'
    artifact_controls: bool = True
    toc_positions: tuple[str, ...] = ('top', 'sidebar', 'reader')
    element_classes: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.name, str):
            raise TypeError('profile name must be a string')
        if not self.name.strip():
            raise ValueError('profile name must not be empty')
        if self.chart_mode not in ('interactive', 'svg'):
            raise ValueError("chart_mode must be 'interactive' or 'svg'")
        if self.stylesheet not in ('theme', 'layout'):
            raise ValueError("stylesheet must be 'theme' or 'layout'")
        for name in (
            'content_only',
            'artifact_controls',
            'include_metadata',
            'include_toc_title',
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f'{name} must be a boolean')
        if self.chart_mode == 'svg' and self.artifact_controls:
            raise ValueError('SVG profiles cannot enable artifact controls')
        if not isinstance(self.toc_positions, tuple):
            raise TypeError('toc_positions must be a tuple')
        if not self.toc_positions or any(
            p not in ('top', 'sidebar', 'reader') for p in self.toc_positions
        ):
            raise ValueError('toc_positions must contain top, sidebar, and/or reader')
        if not isinstance(self.element_classes, Mapping):
            raise TypeError('element_classes must be a mapping')
        classes = {}
        for tag, tokens in self.element_classes.items():
            if not isinstance(tag, str) or not re.fullmatch(r'[a-z][a-z0-9-]*', tag):
                raise ValueError('element class keys must be lowercase HTML tag names')
            if not isinstance(tokens, tuple):
                raise TypeError('element class values must be tuples')
            if any(
                not isinstance(token, str) or not token or re.search(r'\s', token)
                for token in tokens
            ):
                raise ValueError(
                    'element classes must be nonempty tokens without whitespace'
                )
            classes[tag] = tuple(dict.fromkeys(tokens))
        object.__setattr__(self, 'element_classes', MappingProxyType(classes))

    def with_overrides(self, *, name: str, **changes) -> 'RenderingProfile':
        """Derive a profile; supplied tag tuples replace inherited additions."""
        if 'element_classes' in changes:
            if not isinstance(changes['element_classes'], Mapping):
                raise TypeError('element_classes must be a mapping')
            changes['element_classes'] = dict(self.element_classes) | dict(
                changes['element_classes']
            )
        return replace(self, name=name, **changes)


_PROFILES = {
    'rich': RenderingProfile(name='rich'),
    'portable': RenderingProfile(
        name='portable',
        chart_mode='svg',
        artifact_controls=False,
        toc_positions=('top', 'sidebar'),
    ),
    'content': RenderingProfile(
        name='content',
        content_only=True,
        include_metadata=False,
        include_toc_title=False,
        stylesheet='layout',
        artifact_controls=False,
        toc_positions=('top',),
    ),
}


def get_profile(name: str) -> RenderingProfile:
    """Return a built-in profile: rich, portable, or content."""
    if not isinstance(name, str):
        raise TypeError('profile name must be a string')
    try:
        return _PROFILES[name]
    except KeyError:
        raise ValueError(
            f'Unknown profile {name!r}; choose from {", ".join(_PROFILES)}'
        ) from None


def _resolve_profile(profile: str | RenderingProfile) -> RenderingProfile:
    if isinstance(profile, RenderingProfile):
        return profile
    return get_profile(profile)

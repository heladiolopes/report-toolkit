"""Adapters for analytical objects. Optional libraries load only when rendering."""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Protocol
from uuid import uuid4


@dataclass(frozen=True)
class RenderedArtifact:
    html: str


class Adapter(Protocol):
    def render(self, value: Any) -> RenderedArtifact: ...


Predicate = Callable[[Any], bool]


def _has_base_from(value: Any, module_prefix: str) -> bool:
    return any(cls.__module__.startswith(module_prefix) for cls in type(value).__mro__)


class AdapterRegistry:
    def __init__(self) -> None:
        self._entries: list[tuple[Predicate, Adapter]] = []

    def register(self, object_type: type | Predicate, adapter: Adapter) -> None:
        if isinstance(object_type, type):
            predicate = lambda value: isinstance(value, object_type)
        elif callable(object_type):
            predicate = object_type
        else:
            raise TypeError('adapter match must be a type or predicate')
        if not callable(getattr(adapter, 'render', None)):
            raise TypeError('adapter must provide render(value)')
        self._entries.append((predicate, adapter))

    def resolve(self, value: Any) -> Adapter:
        for predicate, adapter in reversed(self._entries):
            if predicate(value):
                return adapter
        name = f'{type(value).__module__}.{type(value).__qualname__}'
        raise TypeError(f'No HTML adapter registered for {name}')


def _is_pandas_styler(value: Any) -> bool:
    if not _has_base_from(value, 'pandas.'):
        return False
    from pandas.io.formats.style import Styler

    return isinstance(value, Styler)


def _is_pandas_dataframe(value: Any) -> bool:
    if not _has_base_from(value, 'pandas.'):
        return False
    from pandas import DataFrame

    return isinstance(value, DataFrame)


def _is_altair_chart(value: Any) -> bool:
    if not _has_base_from(value, 'altair.'):
        return False
    from altair import TopLevelMixin

    return isinstance(value, TopLevelMixin)


def _is_matplotlib_figure(value: Any) -> bool:
    if not _has_base_from(value, 'matplotlib.'):
        return False
    from matplotlib.figure import Figure

    return isinstance(value, Figure)


def _is_plotly_figure(value: Any) -> bool:
    if not _has_base_from(value, 'plotly.'):
        return False
    from plotly.basedatatypes import BaseFigure

    return isinstance(value, BaseFigure)


class PandasStylerAdapter:
    def render(self, value: Any) -> RenderedArtifact:
        return RenderedArtifact(value.to_html())


class PandasDataFrameAdapter:
    def render(self, value: Any) -> RenderedArtifact:
        return RenderedArtifact(value.style.to_html())


class AltairAdapter:
    def __init__(self, *, inline: bool = False) -> None:
        self.inline = inline

    def render(self, value: Any) -> RenderedArtifact:
        try:
            html = value.to_html(
                fullhtml=False,
                output_div=f'reportkit_chart_{uuid4().hex}',
                inline=self.inline,
            )
        except ImportError as exc:
            if self.inline:
                raise ImportError(
                    'Inline Altair HTML requires vl-convert-python; install reportkit[offline]'
                ) from exc
            raise
        return RenderedArtifact(html)


class MatplotlibAdapter:
    def render(self, value: Any) -> RenderedArtifact:
        buffer = BytesIO()
        value.savefig(buffer, format='png', bbox_inches='tight')
        data = base64.b64encode(buffer.getvalue()).decode('ascii')
        return RenderedArtifact(
            f'<img class="reportkit-figure-image" src="data:image/png;base64,{data}" '
            'alt="Matplotlib figure">'
        )


class PlotlyAdapter:
    def render(self, value: Any) -> RenderedArtifact:
        from plotly.io import to_html

        return RenderedArtifact(to_html(value, full_html=False, include_plotlyjs='cdn'))


def default_registry(*, inline_altair: bool = False) -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(_is_pandas_styler, PandasStylerAdapter())
    registry.register(_is_pandas_dataframe, PandasDataFrameAdapter())
    registry.register(_is_altair_chart, AltairAdapter(inline=inline_altair))
    registry.register(_is_matplotlib_figure, MatplotlibAdapter())
    registry.register(_is_plotly_figure, PlotlyAdapter())
    return registry

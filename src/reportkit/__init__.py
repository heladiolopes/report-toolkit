"""Compose analytical reports and render them as HTML."""

from ._template import TemplateError
from .adapters import Adapter, AdapterRegistry, RenderedArtifact, default_registry
from .composer import Report
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
from .themes import Palette, Style, Theme, get_palette, get_theme
from .writer import HTMLWriter

__all__ = [
    'Adapter',
    'AdapterRegistry',
    'Artifact',
    'Columns',
    'Container',
    'Document',
    'HTMLWriter',
    'List',
    'Markdown',
    'Node',
    'Palette',
    'Panel',
    'RawHTML',
    'RenderedArtifact',
    'Report',
    'Section',
    'Style',
    'TemplateError',
    'Theme',
    'default_registry',
    'get_palette',
    'get_theme',
]

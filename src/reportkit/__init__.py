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
from .themes import AutoTheme, Theme, get_theme
from .writer import HTMLWriter

__all__ = [
    'Adapter',
    'AdapterRegistry',
    'Artifact',
    'AutoTheme',
    'Columns',
    'Container',
    'Document',
    'HTMLWriter',
    'List',
    'Markdown',
    'Node',
    'Panel',
    'RawHTML',
    'RenderedArtifact',
    'Report',
    'Section',
    'TemplateError',
    'Theme',
    'default_registry',
    'get_theme',
]

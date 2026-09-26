"""Compose analytical reports and render them as HTML."""

from .adapters import Adapter, AdapterRegistry, RenderedArtifact, default_registry
from .composer import Report
from .model import Artifact, Columns, Container, Document, List, Markdown, Node, Panel, RawHTML, Section
from .writer import HTMLWriter

__all__ = [
    "Adapter",
    "AdapterRegistry",
    "Artifact",
    "Columns",
    "Container",
    "Document",
    "HTMLWriter",
    "List",
    "Markdown",
    "Node",
    "Panel",
    "RawHTML",
    "RenderedArtifact",
    "Report",
    "Section",
    "default_registry",
]

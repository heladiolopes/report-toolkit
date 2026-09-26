"""Compose analytical reports and render them as HTML."""

from .adapters import Adapter, AdapterRegistry, RenderedArtifact, default_registry
from .composer import Report
from .model import Artifact, Columns, Container, Document, Heading, List, Markdown, Node, Section
from .writer import HTMLWriter

__all__ = [
    "Adapter",
    "AdapterRegistry",
    "Artifact",
    "Columns",
    "Container",
    "Document",
    "HTMLWriter",
    "Heading",
    "List",
    "Markdown",
    "Node",
    "RenderedArtifact",
    "Report",
    "Section",
    "default_registry",
]

"""HTML writer for report documents."""

from __future__ import annotations

from datetime import date, datetime
from html import escape
from pathlib import Path

import mistune

from .adapters import AdapterRegistry, default_registry
from .model import Artifact, Columns, Document, Heading, List, Markdown, Node, Section


_PAGE_CSS = "body { margin: 0; background: #f4f6fa; }"
_CSS = """
.reportkit, .reportkit * { box-sizing: border-box; }
.reportkit { max-width: 1040px; margin: 32px auto; padding: 48px clamp(20px, 5vw, 72px); background: white; border: 1px solid #e5eaf0; border-radius: 12px; box-shadow: 0 12px 36px #1d29390c; }
.reportkit { color: #1d2939; font: 16px/1.65 system-ui, sans-serif; }
.reportkit h1, .reportkit h2, .reportkit h3, .reportkit h4, .reportkit h5, .reportkit h6 { color: #14233b; line-height: 1.25; margin: 1.7em 0 .55em; }
.reportkit h1 { font-size: 2.25rem; margin-top: 0; }
.reportkit h2 { font-size: 1.65rem; border-bottom: 1px solid #e5eaf0; padding-bottom: .25em; }
.reportkit p { margin: .6em 0 1.1em; }
.reportkit a { color: #1259a8; }
.reportkit .report-description { color: #52637a; font-size: 1.1rem; }
.reportkit .report-meta { color: #617189; font-size: .875rem; display: flex; flex-wrap: wrap; gap: 1.2rem; }
.reportkit .report-section { margin-top: 2rem; }
.reportkit .report-columns { display: grid; grid-template-columns: repeat(var(--reportkit-columns), minmax(0, 1fr)); gap: 1.5rem; align-items: start; }
.reportkit .report-column-item { min-width: 0; }
.reportkit .report-artifact { margin: 1.5rem 0; min-width: 0; overflow-x: auto; }
.reportkit figcaption { color: #617189; font-size: .875rem; margin-top: .5rem; }
.reportkit .reportkit-figure-image { display: block; max-width: 100%; height: auto; }
.reportkit table { border-collapse: collapse; width: 100%; font-size: .9rem; }
.reportkit th, .reportkit td { border-bottom: 1px solid #e5eaf0; padding: .55rem .75rem; text-align: left; }
.reportkit th { background: #f7f9fc; font-weight: 650; }
.reportkit pre { overflow-x: auto; padding: 1rem; background: #f4f6fa; border-radius: 6px; }
.reportkit code { font-size: .9em; }
@media (max-width: 700px) { .reportkit { margin: 0; border: 0; border-radius: 0; padding: 24px 18px; } .reportkit .report-columns { grid-template-columns: 1fr; } }
""".strip()


class HTMLWriter:
    def __init__(self, *, registry: AdapterRegistry | None = None, inline_altair: bool = False) -> None:
        if registry is not None and inline_altair:
            raise ValueError("Choose a custom registry or inline_altair, not both")
        self.registry = registry if registry is not None else default_registry(inline_altair=inline_altair)
        self._markdown = mistune.create_markdown(escape=True)

    def render(self, document: Document, *, fragment: bool = False) -> str:
        if not isinstance(document, Document):
            raise TypeError("HTMLWriter.render expects a Document")
        content = self._render_document(document)
        if fragment:
            return f"<style>\n{_CSS}\n</style>\n{content}"
        title = escape(document.title or "Report")
        return (
            "<!doctype html>\n<html lang=\"en\">\n<head>\n"
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{title}</title>\n<style>\n{_PAGE_CSS}\n{_CSS}\n</style>\n"
            f"</head>\n<body>\n{content}\n</body>\n</html>\n"
        )

    def write(self, document: Document, path: str | Path, *, fragment: bool = False) -> Path:
        destination = Path(path)
        destination.write_text(self.render(document, fragment=fragment), encoding="utf-8")
        return destination

    def _render_document(self, document: Document) -> str:
        parts = ['<article class="reportkit">']
        if document.title is not None:
            parts.append(f"<header><h1>{escape(document.title)}</h1>")
            if document.description is not None:
                parts.append(f'<p class="report-description">{escape(document.description)}</p>')
            parts.extend(self._metadata(document))
            parts.append("</header>")
        else:
            if document.description is not None:
                parts.append(f'<p class="report-description">{escape(document.description)}</p>')
            parts.extend(self._metadata(document))
        parts.extend(self._render_node(node, 2) for node in document.children)
        parts.append("</article>")
        return "\n".join(parts)

    def _metadata(self, document: Document) -> list[str]:
        if document.author is None and document.date is None:
            return []
        parts = ['<div class="report-meta">']
        if document.author is not None:
            parts.append(f"<span>{escape(document.author)}</span>")
        if document.date is not None:
            value = document.date.isoformat() if isinstance(document.date, (date, datetime)) else document.date
            parts.append(f'<time datetime="{escape(value, quote=True)}">{escape(value)}</time>')
        parts.append("</div>")
        return parts

    def _render_node(self, node: Node, section_level: int) -> str:
        if isinstance(node, Heading):
            return f"<h{node.level}>{escape(node.title)}</h{node.level}>"
        if isinstance(node, Markdown):
            return self._markdown(node.content).strip()
        if isinstance(node, List):
            tag = "ol" if node.ordered else "ul"
            items = "".join(f"<li>{escape(item)}</li>" for item in node.items)
            return f"<{tag}>{items}</{tag}>"
        if isinstance(node, Artifact):
            rendered = self.registry.resolve(node.value).render(node.value)
            caption = f"<figcaption>{escape(node.caption)}</figcaption>" if node.caption else ""
            return f'<figure class="report-artifact">{rendered.html}{caption}</figure>'
        if isinstance(node, Section):
            heading = min(section_level, 6)
            children = "\n".join(self._render_node(child, section_level + 1) for child in node.children)
            return (
                f'<section class="report-section"><h{heading}>{escape(node.title)}</h{heading}>\n'
                f"{children}\n</section>"
            )
        if isinstance(node, Columns):
            children = "\n".join(
                f'<div class="report-column-item">{self._render_node(child, section_level)}</div>'
                for child in node.children
            )
            return (
                f'<div class="report-columns" style="--reportkit-columns: {node.count}">\n'
                f"{children}\n</div>"
            )
        raise TypeError(f"Cannot render node type {type(node).__name__}")

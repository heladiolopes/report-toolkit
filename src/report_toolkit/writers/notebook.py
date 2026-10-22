"""Native notebook display with a minimal column layout."""

from __future__ import annotations

from datetime import date, datetime
from html import escape

import mistune

from ..model import (
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


def _list_html(items: tuple, ordered: bool) -> str:
    tag = 'ol' if ordered else 'ul'
    parts = []
    for item in items:
        if isinstance(item, tuple):
            parts[-1] += _list_html(item, ordered)
        else:
            parts.append('<li>' + escape(item))
    return f'<{tag}>' + ''.join(part + '</li>' for part in parts) + f'</{tag}>'


class NotebookWriter:
    """Display report elements using IPython and ipywidgets.

    Install ``report-toolkit[notebook]`` and use a notebook frontend with widget
    support. Artifact objects use the notebook's native rich representations;
    captions and artifact layout options are ignored.
    """

    def display(self, document: Document) -> None:
        """Display a document in order, using equal-width grids for columns.

        No output is returned or exported. Missing optional dependencies raise
        an ImportError with installation instructions.
        """
        if not isinstance(document, Document):
            raise TypeError('document must be a Document')
        try:
            import IPython.display as ipdisplay
            import ipywidgets as widgets
        except ImportError as exc:
            raise ImportError(
                'Notebook display requires IPython and ipywidgets; '
                'install report-toolkit[notebook]'
            ) from exc

        markdown = mistune.create_markdown(escape=True)

        def html(content: str) -> None:
            ipdisplay.display(ipdisplay.HTML(content))

        def visit(node: Node) -> None:
            if isinstance(node, Artifact):
                ipdisplay.display(node.value)
                return
            if isinstance(node, Markdown):
                html(markdown(node.content))
                return
            if isinstance(node, RawHTML):
                html(node.content)
                return
            if isinstance(node, List):
                html(_list_html(node.items, node.ordered))
                return
            if isinstance(node, Columns):
                outputs = [
                    widgets.Output(layout=widgets.Layout(min_width='0'))
                    for _ in node.children
                ]
                grid = widgets.GridBox(
                    children=outputs,
                    layout=widgets.Layout(
                        grid_template_columns=f'repeat({node.count}, minmax(0, 1fr))',
                        grid_gap='1rem',
                    ),
                )
                ipdisplay.display(grid)
                for child, output in zip(node.children, outputs):
                    # Output contexts normally suppress exceptions. Preserve
                    # normal writer error propagation after closing the capture.
                    failure = None
                    with output:
                        try:
                            visit(child)
                        except Exception as exc:  # noqa: BLE001 - re-raised below
                            failure = exc
                    if failure is not None:
                        raise failure
                return
            if isinstance(node, Document):
                if node.title is not None:
                    html(f'<h1>{escape(node.title)}</h1>')
                for value in (node.description, node.author, node.date):
                    if value is not None:
                        text = (
                            value.isoformat()
                            if isinstance(value, (date, datetime))
                            else value
                        )
                        html(f'<p>{escape(text)}</p>')
            elif isinstance(node, Section):
                html(f'<h{node.level}>{escape(node.title)}</h{node.level}>')
            elif isinstance(node, Panel):
                html(f'<p>{escape(node.title)}</p>')
            else:
                raise TypeError(f'Cannot display node type {type(node).__name__}')
            if isinstance(node, Container):
                for child in node.children:
                    visit(child)

        visit(document)

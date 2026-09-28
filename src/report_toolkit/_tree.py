"""Plain-text inspection of a composed document without rendering artifacts."""

from __future__ import annotations

from textwrap import shorten

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

_Entry = tuple[str, list['_Entry']]


def _preview(text: str) -> str:
    return repr(shorten(text, width=72, placeholder='...'))


def _list_entry(items: tuple, ordered: bool) -> _Entry:
    children: list[_Entry] = []
    for item in items:
        if isinstance(item, str):
            children.append((f'Item({_preview(item)})', []))
        else:
            children[-1][1].append(_list_entry(item, ordered))
    return f'List(ordered={ordered})', children


def _node_entry(node: Node) -> _Entry:
    if isinstance(node, List):
        return _list_entry(node.items, node.ordered)
    if isinstance(node, Artifact):
        value_type = type(node.value)
        label = f'Artifact({value_type.__module__}.{value_type.__qualname__}'
        if node.caption is not None:
            label += f', caption={_preview(node.caption)}'
        label += ')'
    elif isinstance(node, (Markdown, RawHTML)):
        label = f'{type(node).__name__}({_preview(node.content)})'
    elif isinstance(node, Section):
        label = f'Section(level={node.level}, title={_preview(node.title)})'
    elif isinstance(node, (Document, Panel)):
        title = _preview(node.title) if node.title is not None else 'None'
        label = f'{type(node).__name__}(title={title})'
    elif isinstance(node, Columns):
        label = f'Columns(count={node.count})'
    else:
        label = type(node).__name__
    children = (
        [_node_entry(child) for child in node.children]
        if isinstance(node, Container)
        else []
    )
    return label, children


def format_tree(document: Document) -> str:
    label, children = _node_entry(document)
    lines = [label]

    def visit(entries: list[_Entry], prefix: str) -> None:
        for index, (label, children) in enumerate(entries):
            last = index == len(entries) - 1
            lines.append(prefix + ('└── ' if last else '├── ') + label)
            visit(children, prefix + ('    ' if last else '│   '))

    visit(children, '')
    return '\n'.join(lines)

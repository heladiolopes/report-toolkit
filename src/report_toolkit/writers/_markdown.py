"""Shared Markdown parsing for HTML and notebook output."""

import re

import mistune


def _table_code_pipes(markdown, state):
    def visit(tokens, in_table=False):
        for token in tokens:
            if in_table and 'text' in token:
                token['children'] = markdown.inline(token.pop('text'), state.env)
            if in_table and token['type'] == 'codespan':
                # Inline code normally preserves backslashes. In table cells,
                # decode the escaping needed to protect pipes during splitting.
                token['raw'] = re.sub(
                    r'(\\+)\|', lambda m: '\\' * (len(m[1]) // 2) + '|', token['raw']
                )
            if 'children' in token:
                visit(token['children'], in_table or token['type'] == 'table')

    visit(state.tokens)


def create_markdown():
    markdown = mistune.create_markdown(escape=True, plugins=['table'])
    markdown.before_render_hooks.append(_table_code_pipes)
    return markdown

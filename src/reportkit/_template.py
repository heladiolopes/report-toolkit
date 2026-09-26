"""Markdown template composition; no artifact rendering happens here."""

from __future__ import annotations

import json
import re
import string
from collections.abc import Mapping
from contextlib import ExitStack
from datetime import date, datetime
from decimal import Decimal
from html import unescape
from uuid import uuid4

import mistune
from mistune import BlockParser, BlockState

_NAME = r'[A-Za-z_][A-Za-z0-9_]*'
_SCALARS = (str, int, float, bool, Decimal, date, datetime)


class TemplateError(ValueError):
    """Invalid template syntax or context, with a source location."""


class _SourceState(BlockState):
    def append_token(self, token):
        token['_start'] = self.cursor
        super().append_token(token)

    def add_paragraph(self, text):
        start = self.cursor
        super().add_paragraph(text)
        self.tokens[-1].setdefault('_start', start)
        self.tokens[-1]['_end'] = start + len(text)


class _SourceParser(BlockParser):
    state_cls = _SourceState

    def parse_block_html(self, match, state):
        # Mistune uses this rule to end lazy list/blockquote continuations.
        # Template blocks must end those continuations in the same way.
        raw = match.group().lstrip()
        if raw.startswith('{%'):
            return self._methods['template'](match, state)
        if re.fullmatch(self.specification['template_artifact'], match.group()):
            return self._methods['template_artifact'](match, state)
        return super().parse_block_html(match, state)

    def parse_method(self, match, state):
        start = state.cursor
        before = {id(token) for token in state.tokens}
        previous = dict(state.tokens[-1]) if state.tokens else None
        end = super().parse_method(match, state)
        if end:
            added = [token for token in state.tokens if id(token) not in before]
            if added:
                added[0]['_start'] = start
                for index, token in enumerate(added):
                    token['_end'] = (
                        added[index + 1]['_start'] if index + 1 < len(added) else end
                    )
            elif state.tokens and state.tokens[-1] != previous:
                state.tokens[-1]['_end'] = end
        return end


def _escaped(source, position):
    start = position
    while start and source[start - 1] == '\\':
        start -= 1
    return (position - start) % 2 == 1


class _Template:
    def __init__(self, source, context, filename):
        self.source = source.replace('\r\n', '\n').replace('\r', '\n')
        self.context = context
        self.filename = filename
        self.offset = 0
        self.variables = {}
        self.resolved = {}
        self.prefix = 'REPORTKIT' + uuid4().hex + 'VAR'
        self.marker = re.compile(self.prefix + r'\d+END')

    def error(self, message, line=1):
        raise TemplateError(f'{self.filename}:{line + self.offset}: {message}')

    def metadata(self):
        if not re.match(r'\A---[ \t]*\n', self.source):
            return {}
        opening = self.source.index('\n') + 1
        closing = re.search(r'^---[ \t]*(?:\n|$)', self.source[opening:], re.MULTILINE)
        if closing is None:
            self.error('Unclosed YAML front matter')
        try:
            import yaml
        except ImportError as exc:
            raise ImportError(
                'YAML front matter requires reportkit[templates]; '
                'install with: pip install "reportkit[templates]"'
            ) from exc

        class UniqueLoader(yaml.SafeLoader):
            pass

        def mapping(loader, node):
            result = {}
            for key_node, value_node in node.value:
                key = loader.construct_object(key_node)
                if not isinstance(key, str):
                    self.error(
                        'Metadata keys must be strings', key_node.start_mark.line + 2
                    )
                if key in result:
                    self.error(
                        f'Duplicate metadata key: {key}', key_node.start_mark.line + 2
                    )
                result[key] = loader.construct_object(value_node)
            return result

        UniqueLoader.add_constructor('tag:yaml.org,2002:map', mapping)
        try:
            values = yaml.load(
                self.source[opening : opening + closing.start()], Loader=UniqueLoader
            )
        except yaml.YAMLError as exc:
            mark = getattr(exc, 'problem_mark', None)
            self.error('Invalid YAML front matter', mark.line + 2 if mark else 1)
        if values is None:
            values = {}
        if not isinstance(values, dict):
            self.error('YAML front matter must be a metadata mapping')
        for key in values:
            if key not in {'title', 'description', 'author', 'date'}:
                self.error(f'Unknown metadata key: {key}')
        end = opening + closing.end()
        self.offset = self.source[:end].count('\n')
        self.source = self.source[end:]
        return values

    def mask(self):
        # Unique markers let Markdown classify placeholders before substitution.
        # In particular, placeholders in code/HTML stay untouched, and values
        # cannot introduce Markdown structure or executable template syntax.
        def replace(match):
            if _escaped(self.source, match.start()):
                return match.group()
            marker = f'{self.prefix}{len(self.variables)}END'
            line = self.source[: match.start()].count('\n') + 1
            self.variables[marker] = (match.group(), line)
            return marker

        return re.sub(
            r'\{\{[^\n]*?\}\}|\{\{[^\n]*$', replace, self.source, flags=re.MULTILINE
        )

    def value(self, marker):
        expression, line = self.variables[marker]
        match = re.fullmatch(r'\{\{\s*(' + _NAME + r')\s*\}\}', expression)
        if not match:
            self.error('Expected {{ name }} with a simple context key', line)
        name = match[1]
        if name not in self.context:
            self.error(f'Missing template variable: {name}', line)
        value = self.context[name]
        if value is None:
            self.error(f'Template variable {name} cannot be None', line)
        return value

    def scalar(self, marker):
        value = self.value(marker)
        if not isinstance(value, _SCALARS):
            self.error(
                'Artifacts require a standalone placeholder outside lists and blockquotes',
                self.variables[marker][1],
            )
        return value.isoformat() if isinstance(value, (date, datetime)) else str(value)

    def text(self, text):
        return self.marker.sub(lambda m: self.scalar(m.group()), text)

    def restore(self, text):
        def replace(match):
            key = match.group()
            if key in self.resolved:
                # Escape Markdown punctuation, including HTML delimiters.
                # Narrative whitespace follows Markdown's prose conventions.
                value = ' '.join(self.resolved[key].split())
                return ''.join(
                    '\\' + char if char in string.punctuation else char
                    for char in value
                )
            return self.variables[key][0]

        return self.marker.sub(replace, text)

    def inspect(self, tokens, line):
        html_elements = []
        for token in tokens:
            kind = token['type']
            if kind == 'inline_html':
                tag = re.match(r'<(/?)([A-Za-z][\w:-]*)\b', token['raw'])
                if tag:
                    name = tag[2].lower()
                    if tag[1] and name in html_elements:
                        del html_elements[html_elements.index(name) :]
                    elif (
                        not tag[1]
                        and not token['raw'].endswith('/>')
                        and name
                        not in {
                            'area',
                            'base',
                            'br',
                            'col',
                            'embed',
                            'hr',
                            'img',
                            'input',
                            'link',
                            'meta',
                            'param',
                            'source',
                            'track',
                            'wbr',
                        }
                    ):
                        html_elements.append(name)
                continue
            if html_elements or kind in {'block_code', 'codespan', 'block_html'}:
                continue
            if kind == 'template':
                self.error(
                    'Template blocks cannot appear inside lists or blockquotes', line
                )
            if 'children' in token:
                self.inspect(token['children'], line)
            elif 'text' in token:
                self.inspect(
                    mistune.InlineParser()(token['text'], self.state.env), line
                )
            elif kind == 'text':
                raw = token['raw']
                if '{%' in raw:
                    self.error('Template tags must occupy their own line', line)
                for match in self.marker.finditer(raw):
                    key = match.group()
                    self.resolved[key] = self.scalar(key)
            for value in token.get('attrs', {}).values():
                if isinstance(value, str) and self.marker.search(value):
                    self.error(
                        'Variables are supported in narrative text, not link destinations or attributes',
                        line,
                    )

    def plain(self, text):
        def flatten(tokens):
            result = []
            for token in tokens:
                if 'children' in token:
                    result.append(flatten(token['children']))
                elif token['type'] in {'softbreak', 'linebreak'}:
                    result.append(' ')
                elif token['type'] == 'text':
                    result.append(
                        self.marker.sub(
                            lambda m: self.resolved.get(
                                m.group(), self.variables[m.group()][0]
                            ),
                            unescape(token.get('raw', '')),
                        )
                    )
                elif token['type'] != 'inline_html':
                    result.append(
                        self.marker.sub(
                            lambda m: self.variables[m.group()][0],
                            unescape(token.get('raw', '')),
                        )
                    )
            return ''.join(result)

        return flatten(mistune.InlineParser()(text.strip(), self.state.env))

    def parse(self, report):
        source = self.mask()
        if not source.endswith('\n'):
            source += '\n'
        parser = _SourceParser()

        def directive(block, match, state):
            end = state.find_line_end()
            state.append_token(
                {'type': 'template', 'raw': state.src[state.cursor : end].strip()}
            )
            return end

        def placeholder(block, match, state):
            marker = match.group().strip()
            if isinstance(self.value(marker), _SCALARS):
                return None
            end = state.find_line_end()
            state.append_token({'type': 'template_artifact', 'marker': marker})
            return end

        parser.register(
            'template', r'^ {0,3}\{%[^\n]*(?:\n|$)', directive, before='fenced_code'
        )
        parser.register(
            'template_artifact',
            r'^ {0,3}' + self.marker.pattern + r'[ \t]*$',
            placeholder,
            before='fenced_code',
        )
        parser.specification['block_html'] += (
            '|'
            + parser.specification['template']
            + '|'
            + parser.specification['template_artifact']
        )
        # Recognize invalid nested directives too, so they produce useful errors.
        parser.list_rules.insert(0, 'template')
        parser.block_quote_rules.insert(0, 'template')
        state = _SourceState()
        state.process(source)
        parser.parse(state)
        self.state = state
        # Markdown references have document scope, even when their definition
        # occurs inside a list or quote. Give every chunk the same definitions.
        references = []
        for reference in state.env['ref_links'].values():
            label, url = reference['label'], reference['url']
            definition = f'[{label}]: <{url}>'
            if reference.get('title'):
                title = reference['title'].replace('\\', '\\\\').replace('"', '\\"')
                definition += f' "{title}"'
            marker = self.marker.search(definition)
            if marker:
                self.error(
                    'Variables are not supported in reference definitions',
                    self.variables[marker.group()][1],
                )
            references.append(definition)
        refs = '\n'.join(references)

        pending = []
        frames = []
        with ExitStack() as scopes:

            def flush():
                if pending and ''.join(pending).strip():
                    report.markdown(
                        self.restore(''.join(pending))
                        + ('\n\n' + refs if refs.strip() else '')
                    )
                pending.clear()

            for token in state.tokens:
                start, end = token['_start'], token['_end']
                line = source[:start].count('\n') + 1
                kind = token['type']
                raw = source[start:end]
                if kind == 'template':
                    flush()
                    tag = token['raw']
                    match = re.fullmatch(r'\{%\s*(.*?)\s*%\}', tag)
                    if not match:
                        self.error('Malformed template tag', line)
                    instruction = match[1]
                    if instruction in {'endcolumns', 'endpanel'}:
                        expected = instruction[3:]
                        if not frames or frames[-1][0] != expected:
                            self.error(f'Unexpected {instruction}', line)
                        _, scope, _ = frames.pop()
                        scope.close()
                        continue
                    columns = re.fullmatch(r'columns\s+([1-9][0-9]*)', instruction)
                    panel = re.fullmatch(r'panel\s+("(?:[^"\\]|\\.)*")', instruction)
                    artifact = re.fullmatch(
                        r'artifact\s+('
                        + _NAME
                        + r')(?:\s+caption=("(?:[^"\\]|\\.)*"))?',
                        instruction,
                    )
                    if columns or panel:
                        if columns:
                            context = report.columns(int(columns[1]))
                            name = 'columns'
                        else:
                            context = report.panel(
                                self.text(self.quoted(panel[1], line))
                            )
                            name = 'panel'
                        scope = scopes.enter_context(ExitStack())
                        scope.enter_context(context)
                        frames.append((name, scope, line))
                    elif artifact:
                        name = artifact[1]
                        if name not in self.context or self.context[name] is None:
                            self.error(
                                f'Missing or None artifact variable: {name}', line
                            )
                        value = self.context[name]
                        if isinstance(value, _SCALARS):
                            self.error(
                                'An artifact tag requires an analytical object', line
                            )
                        caption = (
                            self.text(self.quoted(artifact[2], line))
                            if artifact[2]
                            else None
                        )
                        report.add(value, caption=caption)
                    else:
                        self.error('Unknown or invalid template tag', line)
                elif kind == 'template_artifact':
                    flush()
                    report.add(self.value(token['marker']))
                elif kind == 'heading':
                    flush()
                    self.inspect([token], line)
                    report.heading(token['attrs']['level'], self.plain(token['text']))
                elif kind == 'paragraph' and self.marker.fullmatch(
                    token['text'].strip()
                ):
                    marker = token['text'].strip()
                    value = self.value(marker)
                    if isinstance(value, _SCALARS):
                        self.resolved[marker] = self.scalar(marker)
                        pending.append(raw)
                    else:
                        flush()
                        report.add(value)
                else:
                    self.inspect([token], line)
                    pending.append(raw)
            flush()
            if frames:
                name, _, line = frames[-1]
                self.error(f'Unclosed {name} block', line)
        report._sections = [[]]
        return report

    def quoted(self, value, line):
        try:
            return json.loads(value)
        except ValueError:
            self.error('Expected a valid double-quoted string', line)


def compose(report_cls, source, context, filename, overrides):
    if not isinstance(source, str):
        raise TypeError('template source must be a string')
    if context is None:
        context = {}
    if not isinstance(context, Mapping):
        raise TypeError('template context must be a mapping')
    template = _Template(source, context, filename)
    metadata = template.metadata()
    metadata.update(overrides)
    try:
        report = report_cls(**metadata)
    except (TypeError, ValueError) as exc:
        raise TemplateError(f'{filename}:1: {exc}') from exc
    return template.parse(report)

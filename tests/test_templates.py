"""Public behavior of the Markdown composition frontend."""

import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from report_toolkit import (
    AdapterRegistry,
    Artifact,
    Columns,
    HTMLWriter,
    Markdown,
    Panel,
    RenderedArtifact,
    Report,
    Section,
    TemplateError,
)


class _Adapter:
    def supports(self, value):
        return isinstance(value, _Chart)

    def render(self, value):
        value.rendered += 1
        return RenderedArtifact(html='<p>Chart</p>')


class _Chart:
    def __init__(self):
        self.rendered = 0


class TemplateTests(unittest.TestCase):
    def registry(self):
        registry = AdapterRegistry()
        registry.register(_Chart, _Adapter())
        return registry

    def test_composition_matches_python_and_defers_rendering(self):
        chart = _Chart()
        template = Report.from_template_string(
            '# Summary\n\nRevenue **{{ growth }}**.\n\n'
            '{% columns 2 %}\n{% panel "Revenue" %}\n'
            '{% artifact chart caption="Trend {{ period }}" %}\n'
            '{% endpanel %}\n{% panel "Again" %}\n{{ chart }}\n'
            '{% endpanel %}\n{% endcolumns %}\n',
            context={'growth': '12%', 'chart': chart, 'period': 'May'},
            title='Sales',
        )
        manual = Report('Sales')
        manual.heading(1, 'Summary')
        manual.markdown('Revenue **12%**.')
        with manual.columns(2):
            with manual.panel('Revenue'):
                manual.add(chart, caption='Trend May')
            with manual.panel('Again'):
                manual.add(chart)
        self.assertEqual(chart.rendered, 0)
        section = template.document.children[0]
        self.assertIsInstance(section, Section)
        columns = section.children[1]
        self.assertIsInstance(columns, Columns)
        self.assertIsInstance(columns.children[0], Panel)
        self.assertIs(columns.children[0].children[0].value, chart)
        self.assertIs(columns.children[1].children[0].value, chart)
        writer = HTMLWriter(registry=self.registry(), toc=True)
        self.assertEqual(
            writer.render(template.document), writer.render(manual.document)
        )
        self.assertEqual(chart.rendered, 4)
        appended = template.markdown('After template')
        self.assertIs(template.document.children[-1], appended)

    def test_headings_and_nested_layout_scopes(self):
        report = Report.from_template_string(
            '# Outer **title**\n{% columns 1 %}\n{% panel "{{ label }}" %}\n'
            'Local\n=====\n{% columns 1 %}\nText\n{% endcolumns %}\n'
            '{% endpanel %}\n{% endcolumns %}\n## Next\nDone\n',
            context={'label': '<Revenue>'},
        )
        outer = report.document.children[0]
        self.assertEqual(outer.title, 'Outer title')
        panel = outer.children[0].children[0]
        self.assertEqual(panel.title, '<Revenue>')
        self.assertEqual(panel.children[0].title, 'Local')
        self.assertIsInstance(panel.children[0].children[0], Columns)
        self.assertEqual(outer.children[1].title, 'Next')
        self.assertIsNone(report.document.title)

    def test_multiline_tags_match_single_line_composition(self):
        chart = _Chart()
        context = {'chart': chart, 'period': 'May'}
        multiline = (
            'Before\n{%\n columns\n 2\n%}\n{% panel\n "Revenue"\n%}\n'
            '{% artifact\n chart\n caption="Trend {{ period }}"\n'
            ' width="full"\n center=false\n expand="always"\n%}\n'
            '{% columns\n 1 %}\n{% panel\n "Nested" %}\nInside\n'
            '{%\n endpanel\n%}\n{%\n endcolumns\n%}\n'
            '{%\n endpanel\n%}\n{%\n endcolumns\n%}\nAfter\n'
        )
        single_line = (
            'Before\n{% columns 2 %}\n{% panel "Revenue" %}\n'
            '{% artifact chart caption="Trend {{ period }}"'
            ' width="full" center=false expand="always" %}\n'
            '{% columns 1 %}\n{% panel "Nested" %}\nInside\n'
            '{% endpanel %}\n{% endcolumns %}\n'
            '{% endpanel %}\n{% endcolumns %}\nAfter\n'
        )
        expected = Report.from_template_string(single_line, context=context)
        for source in (multiline, multiline.replace('\n', '\r\n')):
            with self.subTest(source=source):
                actual = Report.from_template_string(source, context=context)
                artifact = actual.document.children[1].children[0].children[0]
                self.assertIs(artifact.value, chart)
                self.assertEqual(artifact.caption, 'Trend May')
                self.assertEqual(artifact.width, 'full')
                self.assertFalse(artifact.center)
                self.assertEqual(artifact.expand, 'always')
                self.assertEqual(chart.rendered, 0)
                writer = HTMLWriter(registry=self.registry())
                self.assertEqual(
                    writer.render(actual.document), writer.render(expected.document)
                )
                chart.rendered = 0

    def test_multiline_tags_respect_markdown_boundaries_and_quotes(self):
        chart = _Chart()
        for prefix in ('Before', '- Item', '> Quote'):
            with self.subTest(prefix=prefix):
                report = Report.from_template_string(
                    prefix + '\n{% artifact chart\n'
                    ' caption="Literal %} and \\"quote\\"\\nNext"\n%}\nAfter',
                    context={'chart': chart},
                )
                self.assertEqual(
                    [type(node) for node in report.document.children],
                    [Markdown, Artifact, Markdown],
                )
                self.assertEqual(
                    report.document.children[1].caption,
                    'Literal %} and "quote"\nNext',
                )
        source = (
            '```markdown\n{% artifact missing\n caption="Example"\n%}\n```\n\n'
            '    {% panel\n    "Example"\n    %}\n\n'
            '<div>\n{% artifact missing\n%}\n</div>\n'
        )
        actual = Report.from_template_string(source)
        expected = Report()
        expected.markdown(source)
        self.assertEqual(actual.to_html(), expected.to_html())

    def test_multiline_tag_errors_keep_source_locations(self):
        cases = [
            ('{% artifact chart\n caption="Trend"', 'Malformed template tag', 2),
            ('{% artifact chart\n%} trailing', 'Malformed template tag', 2),
            ('Text {% artifact chart\n%}', 'own line', 2),
            ('{% artifact chart\n unknown=true\n%}', 'Unknown artifact attribute', 2),
            ('{% artifact chart\n center=true\n center=false\n%}', 'Duplicate', 2),
            ('{% artifact chart\n caption="Raw\nnewline"\n%}', 'quoted string', 2),
            ('- {% artifact chart\n  %}', 'inside lists or blockquotes', 2),
            ('> {% artifact chart\n> %}', 'inside lists or blockquotes', 2),
            ('{% artifact chart\n%}\n{{ missing }}', 'Missing template variable', 4),
            ('{% panel\n "Notes"\n%}', 'Unclosed panel', 2),
        ]
        for source, message, line in cases:
            with self.subTest(source=source):
                with self.assertRaisesRegex(TemplateError, message) as raised:
                    Report.from_template_string(
                        '\n' + source, context={'chart': _Chart()}
                    )
                self.assertIn(f'<template>:{line}:', str(raised.exception))

    def test_literal_text_code_escapes_and_html(self):
        report = Report.from_template_string(
            '# {{ title }}\n\nValue: **{{ value }}**.\n\n'
            '`{{ absent }}` and \\{{ escaped }}\n\n'
            'Text <span>{{ raw_inline }}</span>.\n\n'
            '```markdown\n{% columns 2 %}\n{{ absent }}\n```\n\n'
            '    {{ indented }}\n\n<div>{{ raw }}</div>\n\n'
            '- {{ value }}\n- `{{ absent }}`\n\n> {{ value }}\n',
            context={'title': '<Monthly>', 'value': '*up* <b> & {{ other }}'},
        )
        html = report.to_html()
        self.assertIn('&lt;Monthly&gt;', html)
        self.assertIn('<strong>*up* &lt;b&gt; &amp; {{ other }}</strong>', html)
        self.assertNotIn('<em>up</em>', html)
        for name in ('absent', 'escaped', 'indented', 'raw', 'raw_inline'):
            self.assertIn('{{ ' + name + ' }}', html)

    def test_references_and_markdown_survive_structural_boundaries(self):
        report = Report.from_template_string(
            '[first][target]\n\n# Heading\n\n{{ chart }}\n\n'
            '> [second][target]\n\n- [third][target]\n\n'
            '> [target]: https://example.org "Reference"\n',
            context={'chart': _Chart()},
        )
        writer = HTMLWriter(registry=self.registry())
        html = writer.render(report.document)
        self.assertEqual(html.count('href="https://example.org"'), 3)
        self.assertIn('<blockquote>', html)
        self.assertIn('<ul>', html)

    def test_invalid_syntax_and_values_have_locations(self):
        cases = [
            ('Text {{ missing }}', {}, 'Missing template variable'),
            ('{{ x.y }}', {}, 'simple context key'),
            ('{{ x', {}, 'simple context key'),
            ('{{ x }}', {'x': None}, 'cannot be None'),
            ('Text {{ chart }}', {'chart': _Chart()}, 'standalone'),
            ('- {{ chart }}', {'chart': _Chart()}, 'standalone'),
            ('> {{ chart }}', {'chart': _Chart()}, 'standalone'),
            ('{% columns 0 %}', {}, 'invalid template tag'),
            ('{% columns 2 %}', {}, 'Unclosed columns'),
            ('{% columns 2 %}\n{% endpanel %}', {}, 'Unexpected endpanel'),
            ('{% if x %}', {}, 'invalid template tag'),
            ('Text {% columns 2 %}', {}, 'own line'),
            ('{% artifact text %}', {'text': 'hello'}, 'analytical object'),
            ('[link]({{ url }})', {'url': 'https://example.org'}, 'destinations'),
        ]
        for source, context, message in cases:
            with self.subTest(source=source):
                with self.assertRaisesRegex(TemplateError, message) as raised:
                    Report.from_template_string('\n' + source, context=context)
                self.assertRegex(str(raised.exception), r'<template>:[23]:')

    def test_file_input_and_scalar_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.md'
            path.write_text(
                'Olá {{ day }}: {{ amount }} / {{ ready }}', encoding='utf-8'
            )
            report = Report.from_template(
                path,
                context={
                    'day': date(2026, 9, 26),
                    'amount': 12.5,
                    'ready': True,
                    'unused': object(),
                },
            )
            self.assertIn('Olá 2026-09-26: 12.5 / True', report.to_html())
            path.write_text('{{ missing }}', encoding='utf-8')
            with self.assertRaisesRegex(TemplateError, 'report.md:1:'):
                Report.from_template(path)

    def test_adjacent_artifacts_and_code_examples(self):
        chart = _Chart()
        report = Report.from_template_string(
            'Before\n{{ chart }}\n{{ chart }}\nAfter\n\n'
            '# `{{ absent }}`\n\n\\{% columns 2 %}\n',
            context={'chart': chart},
        )
        self.assertEqual(
            [type(node) for node in report.document.children],
            [Markdown, Artifact, Artifact, Markdown, Section],
        )
        self.assertEqual(report.document.children[-1].title, '{{ absent }}')
        HTMLWriter(registry=self.registry()).render(report.document)

    def test_ordinary_markdown_round_trips(self):
        samples = [
            '- First\n- Second\n\nAfter\n',
            '- First\n\n  Another paragraph\n\n- Second\n\nAfter\n',
            '> # Heading within quote\n> Text\n\nAfter\n',
            '- Item\n  > Quote\n\n      indented code\n\nAfter\n',
            'Before\n\n---\n\nAfter\n',
            'Text\n\n<div>Raw HTML</div>\n\nAfter\n',
        ]
        for source in samples:
            with self.subTest(source=source):
                actual = Report.from_template_string(source)
                expected = Report()
                expected.markdown(source)
                self.assertEqual(actual.to_html(), expected.to_html())

    def test_layout_tags_end_lists_and_blockquotes(self):
        for content in ('- Item', '> Quote'):
            with self.subTest(content=content):
                report = Report.from_template_string(
                    '{% panel "Notes" %}\n' + content + '\n{% endpanel %}\n'
                    '{{ chart }}\n',
                    context={'chart': _Chart()},
                )
                self.assertIsInstance(report.document.children[0], Panel)
                self.assertIsInstance(report.document.children[1], Artifact)
                self.assertEqual(len(report.document.children[0].children), 1)

    @unittest.skipUnless(importlib.util.find_spec('yaml'), 'PyYAML is not installed')
    def test_yaml_metadata_and_validation(self):
        report = Report.from_template_string(
            '---\ntitle: Sales\nauthor: Analyst\ndate: 2026-09-26\n'
            'description: Monthly\n---\n# Content\n',
            title='Override',
            author=None,
        )
        self.assertEqual(report.document.title, 'Override')
        self.assertIsNone(report.document.author)
        self.assertEqual(report.document.date, date(2026, 9, 26))
        self.assertEqual(report.document.description, 'Monthly')
        for yaml in (
            'title: A\ntitle: B',
            'unknown: x',
            '[a, b]',
            'title: [x]',
            'title: [',
        ):
            with self.subTest(yaml=yaml), self.assertRaises(TemplateError):
                Report.from_template_string('---\n' + yaml + '\n---\nBody')
        with self.assertRaisesRegex(TemplateError, '<template>:5:'):
            Report.from_template_string('---\ntitle: T\n---\n\n{{ missing }}')
        with self.assertRaisesRegex(TemplateError, '<template>:7:'):
            Report.from_template_string(
                '---\ntitle: T\n---\n{% artifact chart\n%}\n\n{{ missing }}',
                context={'chart': _Chart()},
            )

    def test_yaml_dependency_is_lazy(self):
        with patch.dict('sys.modules', {'yaml': None}):
            self.assertIsInstance(
                Report.from_template_string('Hello').document.children[0], Markdown
            )
            with self.assertRaisesRegex(ImportError, r'report-toolkit\[templates\]'):
                Report.from_template_string('---\ntitle: Hi\n---\nHello')
        with self.assertRaisesRegex(TemplateError, 'Unclosed YAML'):
            Report.from_template_string('---\ntitle: Hi')

    @unittest.skipUnless(importlib.util.find_spec('pandas'), 'pandas is not installed')
    def test_optional_pandas_artifact(self):
        import pandas as pd

        value = pd.DataFrame({'sales': [12, 15]}).style
        report = Report.from_template_string('{{ table }}', context={'table': value})
        self.assertIsInstance(report.document.children[0], Artifact)
        self.assertIs(report.document.children[0].value, value)
        self.assertIn('<table', report.to_html())

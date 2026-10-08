import tempfile
import unittest
from datetime import date
from pathlib import Path

from report_toolkit import AdapterRegistry, HTMLWriter, RenderedArtifact, Report


class TextAdapter:
    def render(self, value):
        return RenderedArtifact(f'<strong>{value.text}</strong>')


class TextArtifact:
    def __init__(self, text):
        self.text = text


class WriterTests(unittest.TestCase):
    def setUp(self):
        registry = AdapterRegistry()
        registry.register(TextArtifact, TextAdapter())
        self.writer = HTMLWriter(registry=registry)

    def test_full_document_and_fragment(self):
        report = Report(
            'Sales & Growth',
            description='Quarter <one>',
            author='A & B',
            date=date(2026, 9, 25),
        )
        report.heading(2, 'Summary <here>')
        report.markdown('**Revenue** rose. <script>alert(1)</script>')
        report.list(['North', 'South & West'], ordered=True)
        with report.section('Charts'), report.columns(2):
            report.add(TextArtifact('A'), caption='First & best')
            report.add(TextArtifact('B'))

        html = self.writer.render(report.document)
        fragment = self.writer.render(report.document, fragment=True)
        self.assertTrue(html.startswith('<!doctype html>'))
        self.assertIn('<title>Sales &amp; Growth</title>', html)
        self.assertIn('<h1 class="report-title">Sales &amp; Growth</h1>', html)
        self.assertIn('Quarter &lt;one&gt;', html)
        self.assertIn('datetime="2026-09-25"', html)
        self.assertIn(
            '<h2 id="reporttkt-summary-here" data-reporttkt-heading="2">Summary &lt;here&gt;</h2>',
            html,
        )
        self.assertIn('<strong>Revenue</strong>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertIn('<ol><li>North</li><li>South &amp; West</li></ol>', html)
        self.assertIn('--reporttkt-columns: 2', html)
        self.assertIn('<figcaption>First &amp; best</figcaption>', html)
        self.assertIn('<strong>A</strong>', html)
        self.assertNotIn('<!doctype html>', fragment)
        self.assertIn('<style>', fragment)

    def test_nested_sections_and_file_output(self):
        report = Report()
        with report.section('Outer'), report.section('Inner'):
            report.markdown('Text')
        html = self.writer.render(report.document)
        self.assertIn(
            '<h1 id="reporttkt-outer" data-reporttkt-heading="1">Outer</h1>', html
        )
        self.assertIn(
            '<h2 id="reporttkt-inner" data-reporttkt-heading="2">Inner</h2>', html
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.html'
            self.assertEqual(self.writer.write(report.document, path), path)
            self.assertEqual(path.read_text(encoding='utf-8'), html)
            self.assertIn('<title>Report</title>', report.to_html())
            self.assertEqual(report.write(path), path)

    def test_nested_lists_and_raw_html(self):
        report = Report()
        report.ordered(['Parent & one', ['Child', ['Grandchild']], 'Second'])
        report.unordered(['Another', ['Nested']])
        report.add('<strong>trusted</strong>')
        report.raw_html('<hr>')
        report.markdown('<strong>escaped</strong>')
        html = self.writer.render(report.document)
        self.assertIn(
            '<ol><li>Parent &amp; one<ol><li>Child<ol><li>Grandchild</li></ol></li></ol></li><li>Second</li></ol>',
            html,
        )
        self.assertIn('<ul><li>Another<ul><li>Nested</li></ul></li></ul>', html)
        self.assertIn('<strong>trusted</strong>', html)
        self.assertIn('<hr>', html)
        self.assertIn('&lt;strong&gt;escaped&lt;/strong&gt;', html)

    def test_explicit_report_title_and_untitled_fallback(self):
        report = Report()
        report.paragraph('Intro')
        report.markdown('## Markdown *title* & details')
        report.heading(1, 'Later')
        self.assertIn('<title>Report</title>', report.to_html())
        named = Report('Chosen & title')
        named.heading(1, 'Other heading')
        self.assertIn('<title>Chosen &amp; title</title>', named.to_html())
        self.assertIn(
            '<h1 class="report-title">Chosen &amp; title</h1>', named.to_html()
        )
        self.assertIn('<title>Report</title>', Report().to_html())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.html'
            named.write(path)
            self.assertIn(
                '<title>Chosen &amp; title</title>', path.read_text(encoding='utf-8')
            )
            self.writer.write(named.document, path)
            self.assertIn(
                '<title>Chosen &amp; title</title>', path.read_text(encoding='utf-8')
            )

    def test_unsupported_artifact_has_actionable_error(self):
        report = Report()
        report.add(object())
        with self.assertRaisesRegex(
            TypeError, 'No HTML adapter registered for builtins.object'
        ):
            self.writer.render(report.document)

    def test_custom_adapter_override(self):
        registry = AdapterRegistry()
        registry.register(TextArtifact, TextAdapter())

        class OtherAdapter:
            def render(self, value):
                return RenderedArtifact('<em>override</em>')

        registry.register(TextArtifact, OtherAdapter())
        self.assertIn(
            '<em>override</em>', registry.resolve(TextArtifact('x')).render(None).html
        )


if __name__ == '__main__':
    unittest.main()

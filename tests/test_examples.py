"""Keep the two public authoring examples equivalent as they evolve."""

import importlib.util
import re
import runpy
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch


class _ReportContent(HTMLParser):
    """Compare markup and visible content, ignoring generated IDs and scripts."""

    def __init__(self, html):
        super().__init__()
        self.events = []
        self.hidden = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}:
            self.hidden = tag
        if self.hidden:
            return
        # Preserve layout and navigation; chart/table IDs and inline styles vary.
        selected = tuple(
            (key, value)
            for key, value in attrs
            if key in {'class', 'href'}
            or (key == 'style' and '--reporttkt-columns' in value)
        )
        self.events.append(('start', tag, selected))

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden:
                self.hidden = None
            return
        self.events.append(('end', tag))

    def handle_data(self, data):
        text = ' '.join(data.split())
        if not self.hidden and text:
            self.events.append(('text', text))


@unittest.skipUnless(
    all(
        importlib.util.find_spec(name)
        for name in (
            'pandas',
            'altair',
            'matplotlib',
            'plotly',
            'yaml',
        )
    ),
    'Sales examples require report-toolkit[all]',
)
class ExampleTests(unittest.TestCase):
    def test_sales_examples_render_equivalent_complete_reports(self):
        examples = Path(__file__).resolve().parents[1] / 'examples'
        with patch.object(sys, 'path', [str(examples), *sys.path]):
            builders = [
                runpy.run_path(str(examples / filename))['build_report']
                for filename in ('sales_report.py', 'template_report.py')
            ]
            reports = [build() for build in builders]
        rendered = []
        with tempfile.TemporaryDirectory() as directory:
            for index, report in enumerate(reports):
                output = report.write(
                    Path(directory) / f'{index}.html',
                    toc=True,
                    toc_depth=2,
                )
                html = output.read_text(encoding='utf-8')
                rendered.append(_ReportContent(html).events)
                for marker in (
                    'Sales review',
                    'Report author',
                    '2026-05-01',
                    '$57,500',
                    '43.3% growth',
                    'vegaEmbed',
                    'Plotly.newPlot',
                    'data:image/png;base64,',
                    '<blockquote>',
                    '<pre><code',
                    '<hr',
                    '<ol>',
                    '<ul>',
                    '--reporttkt-columns: 2',
                ):
                    self.assertIn(marker, html)
                self.assertEqual(html.count('<figure class="report-artifact"'), 6)
                self.assertEqual(html.count('<table '), 3)
                self.assertEqual(html.count('class="report-panel"'), 4)
                anchors = set(re.findall(r'id="(reporttkt-[^"]+)"', html))
                links = re.findall(r'href="#(reporttkt-[^"]+)"', html)
                self.assertTrue(links)
                self.assertTrue(set(links) <= anchors)
        self.assertEqual(rendered[0], rendered[1])

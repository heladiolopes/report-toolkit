import logging
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from report_toolkit import (
    AdapterRegistry,
    HTMLWriter,
    Panel,
    RenderedArtifact,
    Report,
    Section,
)


class StructureTests(unittest.TestCase):
    def test_frontends_create_equivalent_sections(self):
        automatic, explicit = Report('Report title'), Report('Report title')
        section = automatic.heading(1, 'Summary')
        automatic.paragraph('Body')
        automatic.heading(2, 'Details')
        automatic.paragraph('Nested body')
        with explicit.section('Summary') as other:
            explicit.paragraph('Body')
            with explicit.section('Details'):
                explicit.paragraph('Nested body')
        self.assertIs(type(section), Section)
        self.assertIs(type(other), Section)
        self.assertEqual((section.title, section.level), ('Summary', 1))
        self.assertEqual(automatic.to_tree(), explicit.to_tree())
        self.assertEqual(automatic.to_html(toc=True), explicit.to_html(toc=True))
        html = automatic.to_html(toc=True)
        self.assertEqual(len(re.findall(r'<h[1-6] id=', html)), 2)
        self.assertEqual(html.count('<li><a href="#'), 2)

    def test_section_validation_and_stored_levels(self):
        self.assertEqual(Section('Default').level, 2)
        for level in (True, 0, 7, '2', 2.5, None):
            with (
                self.subTest(level=level),
                self.assertRaisesRegex(ValueError, 'section level'),
            ):
                Section('Invalid', level=level)
        with self.assertRaisesRegex(TypeError, 'section title'):
            Section(None)
        with self.assertRaises(TypeError):
            Section('Positional level', 3)
        report = Report()
        root = report.heading(4, 'Root')
        with (
            report.columns(2),
            report.panel('Panel'),
            report.section('Child') as child,
            report.section('Deep') as deep,
            report.section('Capped') as capped,
        ):
            pass
        self.assertEqual([n.level for n in (root, child, deep, capped)], [4, 5, 6, 6])
        # The writer respects the model, including explicitly constructed sections.
        direct = Section('Direct', level=1)
        child.append(direct)
        self.assertIn('<h1 id="reporttkt-direct">Direct</h1>', report.to_html())

    def test_heading_transitions_and_intro(self):
        report = Report()
        intro = report.paragraph('Intro')
        first = report.heading(2, 'First')
        text = report.paragraph('Body')
        deep = report.heading(5, 'Deep')
        child = report.paragraph('Child')
        middle = report.heading(3, 'Middle')
        sibling = report.heading(2, 'Sibling')
        top = report.heading(1, 'Top')
        self.assertEqual(report.document.children, (intro, first, sibling, top))
        self.assertEqual(first.children, (text, deep, middle))
        self.assertEqual(deep.children, (child,))
        self.assertIs(middle._parent, first)

    def test_contexts_isolate_headings_and_restore_after_exception(self):
        report = Report()
        outer = report.heading(2, 'Outer')
        with report.section('Explicit') as section:
            local = report.heading(1, 'Local')
            with report.columns(2) as columns:
                with report.panel('Left') as left:
                    report.heading(1, 'Panel heading')
                    report.paragraph('Left body')
                with report.panel('Right') as right:
                    report.paragraph('Right body')
            after_columns = report.paragraph('After columns')
        with (
            self.assertRaisesRegex(RuntimeError, 'stop'),
            report.panel('Interrupted') as interrupted,
        ):
            report.heading(1, 'Interrupted heading')
            raise RuntimeError('stop')
        after = report.paragraph('After')
        self.assertEqual(outer.children, (section, interrupted, after))
        self.assertEqual(local.children, (columns, after_columns))
        self.assertEqual(columns.children, (left, right))
        self.assertEqual(len(left.children[0].children), 1)
        self.assertEqual(right.children[0].content, 'Right body')
        self.assertIn("Panel(title='Left')", report.to_tree())

    def test_normalization_and_invalid_heading_leave_scope_unchanged(self):
        report = Report()
        first = report.heading(1, 'API_v2-results')
        normalized = report.heading(2, '  this-is_an  id ', normalize=True)
        self.assertEqual(first.title, 'API_v2-results')
        self.assertEqual(normalized.title, 'This Is An Id')
        for args, kwargs, error in [
            ((0, 'bad'), {}, ValueError),
            ((1, None), {}, TypeError),
            ((1, 'bad'), {'normalize': 'yes'}, TypeError),
        ]:
            with self.assertRaises(error):
                report.heading(*args, **kwargs)
        text = report.paragraph('Still nested')
        self.assertEqual(normalized.children, (text,))
        with self.assertRaisesRegex(TypeError, 'panel title'):
            Panel(None)

    def test_concat_preserves_source_boundaries_and_copies_containers(self):
        left, right = Report(), Report()
        value = object()
        first = left.heading(1, 'First')
        with left.panel('Panel'):
            left.add(value)
        second = right.heading(3, 'Second')
        right.paragraph('Body')
        combined = left + right
        self.assertEqual(
            [n.title for n in combined.document.children], ['First', 'Second']
        )
        copied = combined.document.children[0]
        self.assertIsNot(copied, first)
        self.assertIsNot(copied.children[0], first.children[0])
        self.assertIs(copied.children[0].children[0].value, value)
        self.assertIsNot(combined.document.children[1], second)
        copied.append(Section('New', level=2))
        self.assertEqual(len(first.children), 1)


class NavigationTests(unittest.TestCase):
    def navigation(self, html):
        return ElementTree.fromstring(
            re.search(r'<nav\b.*?</nav>', html, re.DOTALL).group()
        )

    def test_report_title_is_separate_from_matching_content_sections(self):
        for title in ('Sales & growth', None):
            for fragment in (False, True):
                with self.subTest(title=title, fragment=fragment):
                    report = Report(title)
                    report.heading(1, 'Sales & growth')
                    report.heading(2, 'Summary')
                    report.heading(3, 'Details')
                    report.heading(1, 'Conclusion')
                    report.heading(1, 'Sales & growth')
                    html = report.to_html(toc=True, fragment=fragment)
                    nav = self.navigation(html)
                    self.assertEqual(
                        [a.text for a in nav.iter('a')],
                        [
                            'Sales & growth',
                            'Summary',
                            'Details',
                            'Conclusion',
                            'Sales & growth',
                        ],
                    )
                    self.assertEqual(
                        [a.text for a in nav.findall('./ul/li/a')],
                        ['Sales & growth', 'Conclusion', 'Sales & growth'],
                    )
                    self.assertEqual(html.count('href="#reporttkt-sales-growth"'), 1)
                    self.assertIn(
                        '<h1 id="reporttkt-sales-growth">Sales &amp; growth '
                        '<a class="report-toc-backlink"',
                        html,
                    )
                    if not fragment:
                        expected = (
                            'Sales &amp; growth' if title is not None else 'Report'
                        )
                        self.assertIn(f'<title>{expected}</title>', html)

    def test_title_only_report_has_no_toc(self):
        for title in ('Title', None):
            report = Report(title)
            self.assertNotIn('<nav', report.to_html(toc=True))

    def test_title_metadata_toc_and_content_order(self):
        report = Report('Title <&>', description='Description', author='Author')
        report.paragraph('Intro')
        report.heading(1, 'First')
        report.heading(1, 'Second')
        for fragment in (False, True):
            with self.subTest(fragment=fragment):
                html = report.to_html(toc=True, fragment=fragment)
                article = ElementTree.fromstring(
                    re.search(r'<article\b.*?</article>', html, re.DOTALL).group()
                )
                self.assertEqual(
                    [node.tag for node in article],
                    ['header', 'p', 'div', 'nav', 'p', 'section', 'section'],
                )
                self.assertEqual(article.find('./header/h1').text, 'Title <&>')
                self.assertEqual(
                    len(article.findall('.//h1[@class="report-title"]')), 1
                )
                self.assertEqual(
                    [a.text for a in article.findall('./nav/ul/li/a')],
                    ['First', 'Second'],
                )
                self.assertIn('Title &lt;&amp;&gt;', html)
        without_toc = report.to_html()
        self.assertNotIn('<nav', without_toc)
        self.assertLess(without_toc.index('<header'), without_toc.index('<section'))

    def test_untitled_report_never_infers_visible_title(self):
        report = Report()
        report.raw_html('<h1>Raw heading</h1>')
        report.markdown('# Markdown heading')
        report.heading(1, 'Section heading')
        for fragment in (False, True):
            html = report.to_html(toc=True, fragment=fragment)
            self.assertNotIn('<header', html)
            self.assertNotIn('<h1 class="report-title">', html)
            self.assertEqual(
                [a.text for a in self.navigation(html).iter('a')], ['Section heading']
            )
            if not fragment:
                self.assertIn('<title>Report</title>', html)

    def test_concatenation_has_one_report_title_and_all_sections(self):
        left, right = Report('Left title'), Report('Right title')
        left.heading(1, 'Left title')
        right.heading(1, 'Right title')
        html = (left + right).to_html(toc=True)
        self.assertEqual(html.count('<h1 class="report-title">'), 1)
        self.assertIn('<h1 class="report-title">Left title</h1>', html)
        self.assertEqual(
            [a.text for a in self.navigation(html).iter('a')],
            ['Left title', 'Right title'],
        )

    def test_toc_hierarchy_skipped_levels_and_depth(self):
        report = Report('Report title', author='Author')
        for level, title in [
            (1, 'One'),
            (4, 'Four'),
            (2, 'Two'),
            (3, 'Three'),
            (1, 'Next'),
        ]:
            report.heading(level, title)
        html = report.to_html(toc=True)
        nav = self.navigation(html)
        roots = nav.findall('./ul/li')
        self.assertEqual([n.find('a').text for n in roots], ['One', 'Next'])
        self.assertEqual(
            [n.text for n in roots[0].findall('./ul/li/a')], ['Four', 'Two']
        )
        self.assertEqual(roots[0].find('./ul/li[2]/ul/li/a').text, 'Three')
        self.assertLess(html.index('>Author<'), html.index('<nav'))
        self.assertLess(html.index('<nav'), html.index('<section'))
        limited = self.navigation(report.to_html(toc=True, toc_depth=2))
        self.assertEqual([a.text for a in limited.iter('a')], ['One', 'Two', 'Next'])

    def test_anchors_are_unique_stable_and_do_not_mutate_model(self):
        report = Report('Report title')
        for title in ['A', 'A', 'A-2', '', '!!!', 'São Paulo & <East>']:
            report.heading(1, title)
        before = report.to_tree()
        writer = HTMLWriter(toc=True)
        html = writer.render(report.document)
        ids = re.findall(r'<h1 id="([^"]+)"', html)
        self.assertEqual(
            ids,
            [
                'reporttkt-a',
                'reporttkt-a-2',
                'reporttkt-a-2-2',
                'reporttkt-heading',
                'reporttkt-heading-2',
                'reporttkt-são-paulo-east',
            ],
        )
        self.assertEqual(
            [a.attrib['href'][1:] for a in self.navigation(html).iter('a')], ids
        )
        self.assertIn('São Paulo &amp; &lt;East&gt;', html)
        self.assertEqual(writer.render(report.document), html)
        self.assertEqual(report.to_tree(), before)
        other = Report()
        other.heading(1, 'A')
        self.assertIn('id="reporttkt-a"', writer.render(other.document))

    def test_sections_inherit_levels_and_cap_at_six(self):
        report = Report('Report title')
        report.heading(4, 'Four')
        with (
            report.columns(2),
            report.panel('Panel'),
            report.section('Five'),
            report.section('Six'),
            report.section('Still six'),
        ):
            pass
        html = report.to_html(toc=True)
        self.assertEqual(re.findall(r'<h([1-6]) id=', html), ['4', '5', '6', '6'])
        self.assertEqual(
            [a.text for a in self.navigation(html).iter('a')],
            ['Four', 'Five', 'Six', 'Still six'],
        )

    def test_toc_sources_panel_labels_and_page_title(self):
        report = Report()
        with report.panel('Panel <label>'):
            report.markdown('## Markdown title')
            report.raw_html('<h2>Raw title</h2>')
            report.paragraph('Second panel element')
        report.heading(1, 'Structure')
        with report.section('Explicit'):
            pass
        html = report.to_html(toc=True)
        self.assertEqual(
            [a.text for a in self.navigation(html).iter('a')], ['Structure', 'Explicit']
        )
        self.assertIn('<title>Report</title>', html)
        self.assertIn('<div class="report-panel-title">Panel &lt;label&gt;</div>', html)
        self.assertNotIn('<nav', report.to_html())
        empty = Report()
        with empty.panel('Only panel'):
            empty.paragraph('Body')
        self.assertNotIn('<nav', empty.to_html(toc=True))
        self.assertIn('<title>Report</title>', empty.to_html(toc=True))

    def test_fragment_shortcuts_and_validation(self):
        report = Report('Report title')
        report.heading(2, 'Title')
        fragment = report.to_html(fragment=True, toc=True)
        self.assertNotIn('<!doctype', fragment)
        self.assertIn('<style>', fragment)
        self.assertEqual(self.navigation(fragment).find('./ul/li/a').text, 'Title')
        self.assertNotIn('<nav', report.to_html(toc=True, toc_depth=1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fragment.html'
            report.write(path, fragment=True, toc=True)
            self.assertEqual(path.read_text(), fragment)
        for depth in [True, 0, 7, 1.5, '2']:
            with self.assertRaisesRegex(ValueError, 'toc_depth'):
                HTMLWriter(toc_depth=depth)
        with self.assertRaisesRegex(TypeError, 'toc must'):
            HTMLWriter(toc=1)

    def test_panels_render_as_single_grid_items_and_exclude_artifact_headings(self):
        class HeadingAdapter:
            def render(self, value):
                return RenderedArtifact('<h2>Artifact heading</h2>')

        registry = AdapterRegistry()
        registry.register(object, HeadingAdapter())
        report = Report('Report title')
        report.heading(1, 'Overview')
        with report.columns(2):
            with report.panel('Left'):
                report.paragraph('First')
                report.paragraph('Second')
            with report.panel('Right'):
                report.add(object(), caption='Below')
        html = HTMLWriter(registry=registry, toc=True).render(report.document)
        article = ElementTree.fromstring(
            re.search(r'<article\b.*?</article>', html, re.DOTALL).group()
        )
        columns = article.find('.//div[@class="report-columns"]')
        self.assertEqual(len(columns), 2)
        self.assertEqual(
            [p.text for p in columns[0].findall('./div/p')], ['First', 'Second']
        )
        self.assertEqual(columns[1].find('./div/figure/figcaption').text, 'Below')
        self.assertEqual(
            [a.text for a in self.navigation(html).iter('a')], ['Overview']
        )


class LoggingTests(unittest.TestCase):
    def test_write_logs_path_and_actual_utf8_bytes(self):
        report = Report()
        report.paragraph('São Paulo — 東京')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.html'
            with self.assertLogs('report_toolkit.writer', level=logging.INFO) as logs:
                self.assertEqual(report.write(path), path)
            self.assertEqual(len(logs.records), 1)
            self.assertIn(str(path), logs.output[0])
            self.assertIn(f'{len(path.read_bytes()) / 1024:.1f} KiB', logs.output[0])

    def test_human_readable_size_units(self):
        from report_toolkit.writer import _format_size

        for size, expected in [
            (0, '0 B'),
            (1023, '1023 B'),
            (1024, '1.0 KiB'),
            (1536, '1.5 KiB'),
            (1024**2, '1.0 MiB'),
            (1024**3, '1.0 GiB'),
            (1024**4, '1.0 TiB'),
        ]:
            with self.subTest(size=size):
                self.assertEqual(_format_size(size), expected)

    def test_no_success_log_on_render_or_write_failure(self):
        report = Report()
        with self.assertNoLogs('report_toolkit.writer', level=logging.INFO):
            report.to_html()
            with (
                patch.object(Path, 'write_text', side_effect=OSError('write failed')),
                self.assertRaises(OSError),
            ):
                report.write('unused.html')
            report.add(object())
            with self.assertRaises(TypeError):
                report.write('unused.html')


if __name__ == '__main__':
    unittest.main()

"""Public navigation behavior and optional real-browser layout regressions."""

import re
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from reportkit import HTMLWriter, Report


def navigation(html):
    return ElementTree.fromstring(
        re.search(r'<nav\b.*?</nav>', html, re.DOTALL).group()
    )


def long_report():
    report = Report('Long report')
    for index in range(100):
        report.heading(
            1 if index % 10 == 0 else 2, f'Heading {index} ' + 'long-label-' * 12
        )
        report.paragraph('Report content. ' * 30)
    return report


class NavigationOptionsTests(unittest.TestCase):
    def test_numbering_outline_depth_and_stable_anchors(self):
        report = Report('Title')
        for level, title in [(1, 'A'), (4, 'B'), (2, 'C'), (3, 'D'), (1, 'A')]:
            report.heading(level, title)
        report.markdown('## Embedded')
        report.raw_html('<h2>Raw heading</h2>')
        before = report.to_tree()
        plain = report.to_html()
        numbered = report.to_html(numbered_headings=True, toc=True)
        self.assertEqual(
            [a.text for a in navigation(numbered).iter('a')],
            ['1. A', '1.1. B', '1.2. C', '1.2.1. D', '2. A'],
        )
        self.assertEqual(
            re.findall(r'<h[1-6] id="([^"]+)"', plain),
            re.findall(r'<h[1-6] id="([^"]+)"', numbered),
        )
        for label in ['1. A', '1.1. B', '1.2. C', '1.2.1. D', '2. A']:
            self.assertIn('>' + label + '</h', report.to_html(numbered_headings=True))
        limited = report.to_html(numbered_headings=True, toc=True, toc_depth=2)
        self.assertEqual(
            [a.text for a in navigation(limited).iter('a')], ['1. A', '1.2. C', '2. A']
        )
        self.assertEqual(limited.count('class="report-toc-backlink"'), 5)
        self.assertIn('<h1 class="report-title">Title</h1>', numbered)
        self.assertIn('<h2>Embedded</h2>', numbered)
        self.assertIn('<h2>Raw heading</h2>', numbered)
        self.assertEqual(report.to_tree(), before)
        self.assertEqual(
            plain, report.to_html(numbered_headings=False, toc_position='top')
        )

    def test_backlinks_empty_toc_sidebar_and_shortcuts(self):
        report = Report()
        report.heading(2, 'toc')
        report.heading(3, 'Deep')
        for fragment in (False, True):
            html = report.to_html(toc=True, fragment=fragment)
            target = navigation(html).attrib['id']
            self.assertEqual(html.count(f'href="#{target}"'), 2)
            self.assertEqual(html.count(f'id="{target}"'), 1)
            self.assertNotIn('class="report-toc-backlink"', report.to_html())
            for options in ({'toc': True, 'toc_depth': 1}, {'toc': False}):
                omitted = report.to_html(toc_position='sidebar', **options)
                self.assertNotIn('<nav', omitted)
                self.assertNotIn('class="report-sidebar"', omitted)
                self.assertNotIn('class="report-toc-backlink"', omitted)
            options = {
                'toc': True,
                'toc_position': 'sidebar',
                'numbered_headings': True,
                'fragment': fragment,
            }
            sidebar = report.to_html(**options)
            self.assertNotIn('class="report-toc-backlink"', sidebar)
            self.assertLess(sidebar.index('</nav>'), sidebar.index('<article'))
            with tempfile.TemporaryDirectory() as folder:
                path = report.write(Path(folder) / 'report.html', **options)
                self.assertEqual(path.read_text(), sidebar)
        self.assertNotIn(
            'class="report-sidebar"',
            Report('Only title').to_html(toc=True, toc_position='sidebar'),
        )

    def test_validation_and_writer_reuse(self):
        for value in (1, None, 'yes'):
            with self.assertRaisesRegex(TypeError, 'numbered_headings'):
                HTMLWriter(numbered_headings=value)
        for value in ('left', '', None, 1, []):
            with self.assertRaisesRegex(ValueError, 'toc_position'):
                HTMLWriter(toc_position=value)
        writer = HTMLWriter(numbered_headings=True, toc=True)
        for title in ('First', 'Second', 'First'):
            report = Report()
            report.heading(4, title)
            html = writer.render(report.document)
            self.assertIn(f'>1. {title}', html)
            self.assertEqual(html, writer.render(report.document))


class NavigationBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise unittest.SkipTest('Optional Playwright is not installed')
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch()
        except Exception as exc:
            cls.playwright.stop()
            raise unittest.SkipTest(f'Chromium is unavailable: {exc}') from exc

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def test_long_navigation_layout_scrolling_and_links(self):
        for fragment in (False, True):
            for position in ('top', 'sidebar'):
                with self.subTest(fragment=fragment, position=position):
                    page = self.browser.new_page(
                        viewport={'width': 1440, 'height': 800}
                    )
                    self.addCleanup(page.close)
                    html = long_report().to_html(
                        toc=True,
                        toc_position=position,
                        numbered_headings=True,
                        fragment=fragment,
                    )
                    page.set_content(html)
                    nav = page.locator('nav')
                    if position == 'sidebar':
                        card = page.locator('article').bounding_box()
                        box = nav.bounding_box()
                        self.assertLessEqual(box['x'] + box['width'], card['x'])
                        page.evaluate('window.scrollTo(0, 1200)')
                        self.assertAlmostEqual(nav.bounding_box()['y'], 16, delta=1)
                        self.assertTrue(
                            nav.evaluate('(el) => el.scrollHeight > el.clientHeight')
                        )
                        page_y = page.evaluate('window.scrollY')
                        nav.hover()
                        page.mouse.wheel(0, 100000)
                        page.wait_for_function(
                            '(el) => el.scrollTop + el.clientHeight >= el.scrollHeight - 2',
                            arg=nav.element_handle(),
                        )
                        self.assertEqual(page.evaluate('window.scrollY'), page_y)
                    else:
                        self.assertEqual(
                            nav.evaluate('(el) => el.scrollHeight'),
                            nav.evaluate('(el) => el.clientHeight'),
                        )
                    last_link = nav.locator('a').last
                    target = last_link.get_attribute('href')
                    last_link.click()
                    self.assertEqual(page.evaluate('location.hash'), target)
                    if position == 'top':
                        page.locator(target + ' .report-toc-backlink').click()
                        self.assertEqual(
                            page.evaluate('location.hash'), '#reportkit_toc'
                        )
                        self.assertAlmostEqual(nav.bounding_box()['y'], 0, delta=2)
                    self.assertTrue(
                        page.evaluate(
                            'document.documentElement.scrollWidth <= window.innerWidth'
                        )
                    )

                    if position == 'sidebar':
                        page.set_viewport_size({'width': 390, 'height': 700})
                        self.assertTrue(nav.is_visible())
                        self.assertEqual(page.locator('details, summary').count(), 0)
                        box = nav.bounding_box()
                        card = page.locator('article').bounding_box()
                        self.assertLessEqual(box['y'] + box['height'], card['y'])
                        self.assertEqual(
                            nav.evaluate('(el) => el.scrollHeight'),
                            nav.evaluate('(el) => el.clientHeight'),
                        )
                        last_link.click()
                        self.assertEqual(page.evaluate('location.hash'), target)
                        self.assertTrue(
                            page.evaluate(
                                'document.documentElement.scrollWidth <= window.innerWidth'
                            )
                        )
                        page.emulate_media(media='print')
                        self.assertEqual(
                            nav.evaluate('(el) => el.scrollHeight'),
                            nav.evaluate('(el) => el.clientHeight'),
                        )
                        page.emulate_media(media='screen')
                        page.set_viewport_size({'width': 1440, 'height': 800})
                        self.assertTrue(nav.is_visible())
                        self.assertTrue(
                            nav.evaluate('(el) => el.scrollHeight > el.clientHeight')
                        )

    def test_initial_mobile_navigation_and_theme_isolation(self):
        page = self.browser.new_page(viewport={'width': 390, 'height': 700})
        self.addCleanup(page.close)
        html = ''.join(
            long_report().to_html(
                toc=True, toc_position='sidebar', fragment=True, style={'mode': mode}
            )
            for mode in ('light', 'dark')
        )
        page.set_content(html)
        self.assertEqual(page.locator('nav').count(), 2)
        self.assertEqual(page.locator('details, summary, script').count(), 0)
        for index in range(2):
            self.assertTrue(page.locator('nav').nth(index).is_visible())
        colors = page.locator('article').evaluate_all(
            '(els) => els.map(el => getComputedStyle(el).backgroundColor)'
        )
        self.assertNotEqual(colors[0], colors[1])

    def test_sidebar_without_javascript(self):
        page = self.browser.new_page(
            viewport={'width': 390, 'height': 700}, java_script_enabled=False
        )
        self.addCleanup(page.close)
        page.set_content(long_report().to_html(toc=True, toc_position='sidebar'))
        self.assertTrue(page.locator('nav').is_visible())
        self.assertEqual(page.locator('details, summary, script').count(), 0)
        link = page.locator('nav a').last
        target = link.get_attribute('href')
        link.click()
        self.assertTrue(page.url.endswith(target))

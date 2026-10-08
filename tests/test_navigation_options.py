"""Public navigation behavior and optional real-browser layout regressions."""

import re
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from report_toolkit import HTMLWriter, Report


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

    def test_collapsing_validation_profiles_and_runtime(self):
        from report_toolkit import RenderingProfile

        report = Report()
        report.heading(2, 'Root <&>')
        report.heading(5, 'Deep')
        for value in (1, 0, None, 'yes', []):
            for toc in (False, True):
                with self.assertRaisesRegex(TypeError, 'collapsible_toc'):
                    HTMLWriter(toc=toc, collapsible_toc=value)
                with self.assertRaisesRegex(TypeError, 'collapsible_toc'):
                    report.to_html(toc=toc, collapsible_toc=value)
        for profile in (
            'rich',
            RenderingProfile(name='custom', artifact_controls=False),
        ):
            html = report.to_html(toc=True, profile=profile, collapsible_toc=True)
            self.assertEqual(len(list(navigation(html).iter('button'))), 1)
            self.assertIn('data-reporttkt-navigation="true"', html)
            self.assertIn('<script>', html)
            expanded = report.to_html(toc=True, profile=profile, collapsible_toc=False)
            self.assertEqual(expanded, report.to_html(toc=True, profile=profile))
            self.assertEqual(
                expanded, HTMLWriter(toc=True, profile=profile).render(report.document)
            )
            self.assertEqual(len(list(navigation(expanded).iter('button'))), 0)
            self.assertIn('<script>', expanded)
            with tempfile.TemporaryDirectory() as folder:
                path = report.write(
                    Path(folder) / 'out.html',
                    toc=True,
                    profile=profile,
                )
                self.assertEqual(path.read_text(), expanded)
        for profile in ('portable', 'content'):
            for enabled in (True, False):
                html = report.to_html(
                    toc=True, profile=profile, collapsible_toc=enabled
                )
                self.assertNotIn('<script>', html)
                self.assertEqual(len(list(navigation(html).iter('button'))), 0)
        self.assertNotIn('<script>', report.to_html())
        self.assertNotIn('<script>', report.to_html(toc=True, toc_depth=1))
        flat = Report()
        flat.heading(1, 'Only heading')
        html = flat.to_html(toc=True)
        self.assertIn('<script>', html)
        self.assertEqual(len(list(navigation(html).iter('button'))), 0)

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

    def test_branch_states_scrollspy_and_print(self):
        report = Report('Navigation')
        for level, label in (
            (1, 'A'),
            (3, 'Nested'),
            (5, 'Leaf'),
            (1, 'B'),
            (2, 'Child'),
            (1, 'End'),
        ):
            report.heading(level, label)
            report.raw_html('<div style="height:900px">Content</div>')
        report.markdown('## Excluded Markdown heading')
        report.raw_html('<h1 id="raw">Excluded raw heading</h1>')
        page = self.browser.new_page(viewport={'width': 1440, 'height': 800})
        self.addCleanup(page.close)
        page.set_content(
            report.to_html(toc=True, toc_position='sidebar', collapsible_toc=True)
        )
        page.wait_for_function('document.querySelector("nav [aria-current]") !== null')
        a = page.locator('nav li:has(> a[href="#reporttkt-a"]) > button')
        nested = page.locator('nav li:has(> a[href="#reporttkt-nested"]) > button')
        b = page.locator('nav li:has(> a[href="#reporttkt-b"]) > button')
        nested.focus()
        page.keyboard.press('Enter')
        self.assertEqual(nested.get_attribute('aria-expanded'), 'true')
        b.click()
        a.click()
        self.assertFalse(page.locator('nav a[href="#reporttkt-leaf"]').is_visible())
        self.assertEqual(nested.get_attribute('aria-expanded'), 'true')
        self.assertEqual(b.get_attribute('aria-expanded'), 'true')
        page.evaluate('window.dispatchEvent(new Event("scroll"))')
        page.wait_for_timeout(50)
        self.assertEqual(a.get_attribute('aria-expanded'), 'false')
        a.focus()
        page.keyboard.press('Space')
        self.assertTrue(page.locator('nav a[href="#reporttkt-leaf"]').is_visible())
        a.click()
        page.locator('#reporttkt-leaf').evaluate(
            '(el) => window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 20)'
        )
        page.wait_for_function(
            'document.querySelector("nav [aria-current]").hash === "#reporttkt-leaf"'
        )
        self.assertEqual(a.get_attribute('aria-expanded'), 'true')
        self.assertEqual(page.evaluate('location.hash'), '')
        page.locator('#reporttkt-a').evaluate(
            '(el) => window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 20)'
        )
        page.wait_for_function(
            'document.querySelector("nav [aria-current]").hash === "#reporttkt-a"'
        )
        a.click()
        page.evaluate('location.hash = "#reporttkt-leaf"')
        page.wait_for_function(
            'document.querySelector("nav [aria-current]").hash === "#reporttkt-leaf"'
        )
        self.assertEqual(a.get_attribute('aria-expanded'), 'true')
        a.click()
        state = page.locator('nav button').evaluate_all(
            '(els) => els.map(el => el.getAttribute("aria-expanded"))'
        )
        page.emulate_media(media='print')
        self.assertTrue(page.locator('nav a[href="#reporttkt-leaf"]').is_visible())
        self.assertFalse(a.is_visible())
        self.assertEqual(
            page.locator('nav [aria-current]').evaluate(
                '(el) => getComputedStyle(el).boxShadow'
            ),
            'none',
        )
        page.emulate_media(media='screen')
        self.assertEqual(
            page.locator('nav button').evaluate_all(
                '(els) => els.map(el => el.getAttribute("aria-expanded"))'
            ),
            state,
        )

    def test_initial_position_depth_filter_fragments_and_resizing(self):
        report = Report('Depth')
        for level, label in (
            (2, 'Root'),
            (5, 'Excluded'),
            (3, 'Included'),
            (6, 'Deep'),
            (2, 'End'),
        ):
            report.heading(level, label)
            report.raw_html('<div style="height:900px">Content</div>')
        page = self.browser.new_page(viewport={'width': 1440, 'height': 800})
        self.addCleanup(page.close)
        html = report.to_html(toc=True, toc_depth=3, toc_position='sidebar')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'initial.html'
            path.write_text(html)
            page.goto(path.as_uri() + '#reporttkt-deep')
            page.wait_for_function(
                'document.querySelector("nav [aria-current]").hash === "#reporttkt-included"'
            )
        page.set_content(
            html.replace(
                '<script>',
                '<script>history.replaceState(null, "", location.pathname); requestAnimationFrame(() => document.querySelector("#reporttkt-included").scrollIntoView());',
                1,
            )
        )
        page.wait_for_function(
            'document.querySelector("nav [aria-current]").hash === "#reporttkt-included"'
        )
        page.set_content(report.to_html(toc=True, toc_depth=3, collapsible_toc=False))
        self.assertEqual(page.locator('nav button').count(), 0)
        page.locator('#reporttkt-excluded').evaluate(
            '(el) => window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 20)'
        )
        page.wait_for_function(
            'document.querySelector("nav [aria-current]").hash === "#reporttkt-root"'
        )
        page.locator('#reporttkt-deep').evaluate(
            '(el) => window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 20)'
        )
        page.wait_for_function(
            'document.querySelector("nav [aria-current]").hash === "#reporttkt-included"'
        )
        page.add_style_tag(content='* { overflow-anchor: none; }')
        page.locator('article section > div').first.evaluate(
            '(el) => el.style.height = "4000px"'
        )
        page.wait_for_function(
            'document.querySelector("nav [aria-current]").hash === "#reporttkt-root"'
        )
        fragments = ''.join(
            report.to_html(
                toc=True,
                fragment=True,
                toc_position='sidebar',
                collapsible_toc=True,
                style={'mode': mode},
            )
            for mode in ('light', 'dark')
        )
        page.set_content(fragments)
        self.assertEqual(
            page.locator('nav[data-reporttkt-navigation-ready]').count(), 2
        )
        page.locator('nav').nth(1).locator('a').first.click()
        page.wait_for_function(
            'document.querySelectorAll("article")[1].querySelector("h2").getBoundingClientRect().top <= 24'
        )
        self.assertEqual(
            page.locator('nav')
            .nth(0)
            .locator('button')
            .first.get_attribute('aria-expanded'),
            'true',
        )
        self.assertEqual(
            page.locator('nav').nth(1).locator('[aria-current]').count(), 1
        )

    def test_toc_depth_styles_and_accessible_link_states(self):
        report = Report('Hierarchy')
        for level in range(1, 7):
            report.heading(level, f'Level {level} ' + 'long-label-' * 12)
        report.heading(1, 'Next section')
        report.list(['Ordinary content list'])
        page = self.browser.new_page(viewport={'width': 1440, 'height': 800})
        self.addCleanup(page.close)
        for fragment in (False, True):
            for position in ('top', 'sidebar'):
                for mode in ('light', 'dark'):
                    with self.subTest(fragment=fragment, position=position, mode=mode):
                        page.set_content(
                            report.to_html(
                                toc=True,
                                collapsible_toc=False,
                                toc_position=position,
                                fragment=fragment,
                                style={'mode': mode},
                            )
                        )
                        nav = page.locator('nav')
                        lists = nav.locator('ul')
                        self.assertEqual(
                            lists.evaluate_all(
                                '(els) => els.map(el => getComputedStyle(el).listStyleType)'
                            ),
                            ['none'] * 6,
                        )
                        self.assertEqual(
                            lists.evaluate_all(
                                '(els) => els.map(el => parseFloat(getComputedStyle(el).marginBottom))'
                            ),
                            [0] * 6,
                        )
                        links = nav.locator('a')
                        nav.locator('[aria-current]').evaluate_all(
                            '(els) => els.forEach(el => el.removeAttribute("aria-current"))'
                        )
                        styles = links.evaluate_all("""(els) => els.map(el => {
                            const style = getComputedStyle(el);
                            return {
                                x: el.getBoundingClientRect().x,
                                size: parseFloat(style.fontSize),
                                weight: Number(style.fontWeight),
                                padding: parseFloat(style.paddingTop)
                            };
                        })""")
                        root_size = styles[0]['size']
                        rem = page.evaluate(
                            'parseFloat(getComputedStyle(document.documentElement).fontSize)'
                        )
                        for depth, (ratio, weight, padding) in enumerate(
                            zip(
                                (1, 0.95, 0.9, 0.875, 0.85, 0.825),
                                (400, 400, 400, 400, 400, 400),
                                (0.3, 0.25, 0.2, 0.175, 0.15, 0.125),
                            )
                        ):
                            self.assertAlmostEqual(
                                styles[depth]['x'] - styles[0]['x'],
                                depth * rem,
                                delta=0.1,
                            )
                            self.assertAlmostEqual(
                                styles[depth]['size'], root_size * ratio, delta=0.1
                            )
                            self.assertEqual(styles[depth]['weight'], weight)
                            self.assertAlmostEqual(
                                styles[depth]['padding'], rem * padding, delta=0.1
                            )
                        self.assertEqual(styles[0], styles[-1])
                        content_list = page.locator('article ul').last
                        self.assertNotEqual(
                            content_list.evaluate(
                                '(el) => getComputedStyle(el).listStyleType'
                            ),
                            'none',
                        )
                        for index in (0, 5):
                            link = links.nth(index)
                            link.focus()
                            self.assertTrue(
                                link.evaluate('(el) => el.matches(":focus-visible")')
                            )
                            self.assertEqual(
                                link.evaluate(
                                    '(el) => getComputedStyle(el).outlineStyle'
                                ),
                                'solid',
                            )
                            link.evaluate(
                                '(el) => el.setAttribute("aria-current", "location")'
                            )
                            shadow = link.evaluate(
                                '(el) => getComputedStyle(el).boxShadow'
                            )
                            self.assertIn('inset', shadow)
                            self.assertIn('3px', shadow)
                            self.assertEqual(
                                link.evaluate(
                                    '(el) => getComputedStyle(el).fontWeight'
                                ),
                                '700',
                            )
                            self.assertNotEqual(
                                link.evaluate(
                                    '(el) => getComputedStyle(el).backgroundColor'
                                ),
                                'rgba(0, 0, 0, 0)',
                            )
                        page.set_viewport_size({'width': 390, 'height': 700})
                        self.assertTrue(
                            page.evaluate(
                                'document.documentElement.scrollWidth <= window.innerWidth'
                            )
                        )
                        page.set_viewport_size({'width': 1440, 'height': 800})

        skipped = Report()
        for level, label in ((2, 'Root'), (5, 'Skipped'), (3, 'Sibling')):
            skipped.heading(level, label)
        page.set_content(skipped.to_html(toc=True))
        page.locator('nav button').evaluate_all(
            '(els) => els.forEach(el => { if (el.getAttribute("aria-expanded") === "false") el.click(); })'
        )
        sizes = page.locator('nav a').evaluate_all(
            '(els) => els.map(el => parseFloat(getComputedStyle(el).fontSize))'
        )
        self.assertAlmostEqual(sizes[0], root_size, delta=0.1)
        self.assertAlmostEqual(sizes[1], root_size * 0.95, delta=0.1)
        self.assertEqual(sizes[1], sizes[2])

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
                        collapsible_toc=False,
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
                    if position == 'sidebar':
                        page.locator('article').evaluate(
                            '(el) => { const space = document.createElement("div"); space.style.height = "100vh"; el.append(space); }'
                        )
                        page.locator(target).evaluate(
                            '(el) => window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 20)'
                        )
                        page.wait_for_function(
                            '(target) => document.querySelector("nav [aria-current]").hash === target',
                            arg=target,
                        )
                        self.assertTrue(
                            last_link.evaluate("""el => {
                            const nav = el.closest('nav').getBoundingClientRect();
                            const link = el.getBoundingClientRect();
                            return link.top >= nav.top - 1 && link.bottom <= nav.bottom + 1;
                        }""")
                        )
                    last_link.click()
                    self.assertEqual(page.evaluate('location.hash'), target)
                    if position == 'top':
                        page.locator(target + ' .report-toc-backlink').click()
                        self.assertEqual(
                            page.evaluate('location.hash'), '#reporttkt_toc'
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
        self.assertEqual(page.locator('details, summary').count(), 0)
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
        self.assertEqual(page.locator('details, summary').count(), 0)
        self.assertEqual(page.locator('nav a:visible').count(), 100)
        self.assertEqual(page.locator('nav button:visible').count(), 0)
        link = page.locator('nav a').last
        target = link.get_attribute('href')
        link.click()
        self.assertTrue(page.url.endswith(target))

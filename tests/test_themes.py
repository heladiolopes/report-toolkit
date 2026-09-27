"""Public theme behavior and rendering integration."""

import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

from reportkit import AutoTheme, HTMLWriter, Report, Theme, get_theme


class ThemeTests(unittest.TestCase):
    def setUp(self):
        self.report = Report('Theme preview', author='Analyst')
        self.report.heading(1, 'Summary')
        self.report.markdown('A [link](https://example.org) and `code`.\n\n> Note')
        with self.report.columns(2), self.report.panel('Details'):
            self.report.paragraph('Content')

    def test_presets_and_output_shortcuts_preserve_document(self):
        before = self.report.to_tree()
        original = self.report.to_html()
        self.assertEqual(original, self.report.to_html(theme='light'))
        with tempfile.TemporaryDirectory() as directory:
            for name in ('light', 'dark', 'paper', 'ink', 'auto', 'auto-paper'):
                for fragment in (False, True):
                    with self.subTest(name=name, fragment=fragment):
                        html = self.report.to_html(theme=name, fragment=fragment)
                        writer = HTMLWriter(theme=get_theme(name))
                        self.assertEqual(
                            html, writer.render(self.report.document, fragment=fragment)
                        )
                        path = self.report.write(
                            Path(directory) / 'report.html',
                            theme=name,
                            fragment=fragment,
                        )
                        self.assertEqual(path.read_text(), html)
                        self.assertEqual(
                            writer.write(self.report.document, path, fragment=fragment),
                            path,
                        )
                        self.assertEqual(path.read_text(), html)
                        self.assertEqual('body {' in html, not fragment)
                        self.assertEqual('<!doctype html>' in html, not fragment)
                        self.assertIn('grid-template-columns: 1fr', html)
                        self.assertIn(' .reportkit-figure-image {', html)
        self.assertEqual(before, self.report.to_tree())
        self.assertEqual(original, self.report.to_html())

    def test_custom_tokens_are_copied_and_overrides_inherit(self):
        tokens = {'accent': '#2457a7'}
        custom = Theme(name='custom', tokens=tokens, css='& h2 { font-style: italic; }')
        tokens['accent'] = 'red'
        derived = custom.with_overrides(
            name='derived', tokens={'content_width': '1120px'}
        )
        self.assertEqual(derived.tokens['accent'], '#2457a7')
        self.assertEqual(derived.css, custom.css)
        with self.assertRaises(TypeError):
            custom.tokens['accent'] = 'red'
        html = self.report.to_html(theme=derived)
        self.assertIn('--reportkit-content-width: 1120px;', html)
        self.assertIn('--reportkit-accent: #2457a7;', html)
        self.assertIn(' h2 { font-style: italic; }', html)
        self.assertNotIn('& h2', html)
        self.assertEqual(custom.with_overrides(name='clean', css='').css, '')

    def test_custom_fragment_scopes_depend_on_content_not_only_name(self):
        themes = [
            get_theme(name).with_overrides(name='custom') for name in ('light', 'dark')
        ]
        fragments = [self.report.to_html(theme=t, fragment=True) for t in themes]
        scopes = [
            re.search(
                r'<article class="reportkit" data-reportkit-theme="([^"]+)"', html
            )[1]
            for html in fragments
        ]
        self.assertNotEqual(*scopes)
        for html, scope, other in zip(fragments, scopes, reversed(scopes)):
            self.assertIn(f'.reportkit:where([data-reportkit-theme="{scope}"])', html)
            self.assertNotIn(other, html)
            self.assertNotIn('body {', html)
            self.assertNotRegex(html, r'\.reportkit(?=[\s,{])')

    def test_automatic_pair_conditions_include_custom_css(self):
        light = get_theme('paper').with_overrides(
            name='custom-light', css='& p { letter-spacing: 1px; }'
        )
        dark = get_theme('ink').with_overrides(
            name='custom-dark', css='& p { font-style: italic; }'
        )
        html = self.report.to_html(theme=AutoTheme(light=light, dark=dark))
        light_rules, dark_rules = html.split('@media (prefers-color-scheme: dark)', 1)
        self.assertIn('color-scheme: light;', light_rules)
        self.assertIn('@media not all and (prefers-color-scheme: dark)', light_rules)
        self.assertIn('letter-spacing: 1px', light_rules)
        self.assertIn('color-scheme: dark;', dark_rules)
        self.assertIn('font-style: italic', dark_rules)
        self.assertNotIn('letter-spacing', dark_rules)
        self.assertNotIn('<script', html)

    def test_invalid_theme_inputs(self):
        cases = [
            (ValueError, lambda: HTMLWriter(theme='missing')),
            (TypeError, lambda: self.report.to_html(theme=42)),
            (ValueError, lambda: Theme(name='')),
            (ValueError, lambda: Theme(name='custom', mode='auto')),
            (TypeError, lambda: Theme(name='custom', tokens=[])),
            (ValueError, lambda: Theme(name='custom', tokens={'typo': 'red'})),
            (TypeError, lambda: Theme(name='custom', tokens={'accent': 42})),
            (ValueError, lambda: Theme(name='custom', tokens={'accent': ' '})),
            (TypeError, lambda: Theme(name='custom', css=None)),
            (TypeError, lambda: AutoTheme(light='light', dark=get_theme('dark'))),
            (
                ValueError,
                lambda: AutoTheme(light=get_theme('dark'), dark=get_theme('light')),
            ),
        ]
        for error, operation in cases:
            with self.subTest(operation=operation), self.assertRaises(error):
                operation()

    def test_css_cannot_close_style_element(self):
        custom = Theme(name='custom', css='&::after { content: "</style>"; }')
        html = self.report.to_html(theme=custom)
        self.assertEqual(html.count('</style>'), 1)
        self.assertIn(r'\3c /style>', html)

    def test_preset_text_contrast(self):
        def luminance(color):
            channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [
                c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
                for c in channels
            ]
            return sum(
                c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722))
            )

        for name in ('light', 'dark', 'paper', 'ink'):
            tokens = get_theme(name).tokens
            for foreground in ('text', 'heading', 'accent', 'description', 'muted'):
                for background in ('background', 'surface', 'table_header'):
                    with self.subTest(
                        name=name, foreground=foreground, background=background
                    ):
                        values = sorted(
                            (
                                luminance(tokens[foreground]),
                                luminance(tokens[background]),
                            )
                        )
                        self.assertGreaterEqual(
                            (values[1] + 0.05) / (values[0] + 0.05), 4.5
                        )

    @unittest.skipUnless(importlib.util.find_spec('pandas'), 'requires pandas')
    def test_explicit_styler_styles_survive_dark_theme(self):
        import pandas as pd

        styler = pd.DataFrame({'Value': [1]}).style.set_properties(
            **{'color': '#123456', 'background-color': '#abcdef'}
        )
        self.report.add(styler, caption='Styled data')
        html = self.report.to_html(theme='dark')
        self.assertIn('color: #123456;', html)
        self.assertIn('background-color: #abcdef;', html)
        self.assertIn('<figcaption>Styled data</figcaption>', html)
        self.assertNotIn('!important', html)

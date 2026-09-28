"""Public style configuration and HTML rendering integration."""

import re
from dataclasses import FrozenInstanceError
from itertools import product
from types import MappingProxyType

import pytest

from report_toolkit import (
    HTMLWriter,
    Palette,
    Report,
    Style,
    Theme,
    get_palette,
    get_theme,
)

PALETTES = ('slate', 'azure', 'parchment', 'ember')
MODES = ('light', 'dark', 'auto')


def test_public_import_paths():
    from report_toolkit import themes

    for public in (Style, Theme, Palette, get_theme, get_palette):
        assert getattr(themes, public.__name__) is public


@pytest.fixture
def report():
    report = Report('Style preview', author='Analyst')
    report.heading(1, 'Summary')
    report.markdown('A [link](https://example.org) and `code`.\n\n> Note')
    with report.columns(2), report.panel('Details'):
        report.paragraph('Content')
    return report


def scope(html):
    return re.search(r'data-reporttkt-theme="([^"]+)"', html)[1]


def test_default_inputs_preserve_appearance(report):
    original = report.to_html()
    for style in (None, {}, Style(), {'mode': 'light'}, MappingProxyType({})):
        assert report.to_html(style=style) == original
    for key, value in {
        'font_family': 'Roboto, "Noto Sans", sans-serif',
        'font_size': '16px',
        'line_height': '1.5',
        'content_width': '1040px',
        'page_margin': '32px auto',
        'content_padding': '48px clamp(20px, 5vw, 72px)',
        'radius': '5px',
        'shadow_geometry': '0 18px 42px',
        'title_size': '2.5rem',
        'table_border_width': '1px',
        'cell_padding': '.25rem .75rem',
        'background': '#ffffff',
        'page_background': '#f5f5f5',
        'text': '#262626',
        'accent': '#2563eb',
    }.items():
        assert f'--reporttkt-{key.replace("_", "-")}: {value};' in original
    assert 'grid-template-columns: 1fr' in original
    assert '@font-face' not in original
    assert '@import' not in original


@pytest.mark.parametrize(
    'palette,mode,fragment', list(product(PALETTES, MODES, (False, True)))
)
def test_style_inputs_and_exports_agree(report, tmp_path, palette, mode, fragment):
    before = report.to_tree()
    mapping = {'theme': 'default', 'palette': palette, 'mode': mode}
    html = report.to_html(style=mapping, fragment=fragment)
    objects = Style(theme=get_theme('default'), palette=get_palette(palette), mode=mode)
    assert report.to_html(style=Style(**mapping), fragment=fragment) == html
    writer = HTMLWriter(style=objects)
    assert writer.render(report.document, fragment=fragment) == html
    path = report.write(tmp_path / 'report.html', style=mapping, fragment=fragment)
    assert path.read_text() == html
    assert writer.write(report.document, path, fragment=fragment) == path
    assert path.read_text() == html
    assert ('body {' in html) is not fragment
    assert ('<!doctype html>' in html) is not fragment
    assert ('@media (prefers-color-scheme: dark)' in html) is (mode == 'auto')
    selected = 'light' if mode == 'auto' else mode
    assert (
        f'--reporttkt-background: {getattr(get_palette(palette), selected)["background"]};'
        in html
    )
    assert f'color-scheme: {selected};' in html
    assert report.to_tree() == before


def test_custom_objects_copy_freeze_and_derive(report):
    tokens = {'content_width': '1120px'}
    colors = {'accent': '#2457a7'}
    theme = Theme(name='custom', tokens=tokens, css='& h2 { font-style: italic; }')
    palette = Palette(name='custom', light=colors)
    tokens['content_width'] = '0'
    colors['accent'] = 'red'
    derived = theme.with_overrides(name='derived', tokens={'font_size': '18px'})
    derived_palette = palette.with_overrides(name='derived', dark={'accent': '#91baff'})
    assert derived.tokens['content_width'] == '1120px'
    assert derived.css == theme.css
    assert derived_palette.light['accent'] == '#2457a7'
    assert derived_palette.dark['accent'] == '#91baff'
    assert theme.tokens['font_size'] == '16px'
    assert palette.dark == get_palette('slate').dark
    assert theme.with_overrides(name='clean', css='').css == ''
    assert palette.with_overrides(name='same', light={}).light == palette.light
    assert Theme(name='empty').tokens == get_theme('default').tokens
    for mapping in (theme.tokens, palette.light, palette.dark):
        with pytest.raises(TypeError):
            mapping['anything'] = 'red'
    style = Style(theme=derived, palette=derived_palette, mode='auto')
    with pytest.raises(FrozenInstanceError):
        style.mode = 'dark'
    html = report.to_html(style=style)
    light, dark = html.split('@media (prefers-color-scheme: dark)', 1)
    assert '--reporttkt-accent: #2457a7;' in light
    assert '--reporttkt-accent: #91baff;' in dark
    assert 'color-scheme: light;' in light
    assert 'color-scheme: dark;' in dark
    assert '--reporttkt-content-width: 1120px;' in light
    assert '--reporttkt-content-width:' not in dark
    assert html.count('font-style: italic') == 1
    assert html.index('font-style: italic') > html.index(
        '@media (prefers-color-scheme: dark)'
    )
    assert '& h2' not in html
    assert '<script' not in html


@pytest.mark.parametrize('position', ('top', 'sidebar'))
def test_fragment_scopes_and_navigation(report, position):
    fragments = [
        report.to_html(
            style={'palette': name}, fragment=True, toc=True, toc_position=position
        )
        for name in PALETTES
    ]
    assert len({scope(html) for html in fragments}) == len(PALETTES)
    for html in fragments:
        assert f'.reporttkt:where([data-reporttkt-theme="{scope(html)}"])' in html
        assert 'body {' not in html
        assert not re.search(r'\.reporttkt(?=[\s,{])', html)
        assert set(re.findall(r'data-reporttkt-theme="([^"]+)"', html)) == {scope(html)}
        assert '--reporttkt-toc-text: var(--reporttkt-text);' in html
        assert '--reporttkt-toc-background: var(--reporttkt-surface);' in html
        assert '--reporttkt-toc-accent: var(--reporttkt-accent);' in html
        assert '.report-toc a:focus-visible' in html


def test_scopes_and_output_depend_on_content_not_mapping_order(report):
    tokens = {'font_size': '18px', 'content_width': '1120px'}
    colors = {'accent': '#123456', 'text': '#333333'}
    theme = Theme(name='custom', tokens=tokens)
    palette = Palette(name='custom', light=colors)
    baseline = report.to_html(style=Style(theme=theme, palette=palette))
    reordered = Style(
        theme=Theme(name='custom', tokens=dict(reversed(list(tokens.items())))),
        palette=Palette(name='custom', light=dict(reversed(list(colors.items())))),
    )
    assert report.to_html(style=reordered) == baseline
    variants = [
        Style(
            theme=theme.with_overrides(name='custom', tokens={'font_size': '20px'}),
            palette=palette,
        ),
        Style(
            theme=theme.with_overrides(
                name='custom', css='& p { font-style: italic; }'
            ),
            palette=palette,
        ),
        Style(
            theme=theme,
            palette=palette.with_overrides(name='custom', light={'accent': 'red'}),
        ),
        Style(
            theme=theme,
            palette=palette.with_overrides(name='custom', dark={'accent': 'red'}),
        ),
        Style(theme=theme, palette=palette, mode='dark'),
        Style(theme=theme, palette=palette, mode='auto'),
    ]
    scopes = [scope(baseline), *(scope(report.to_html(style=s)) for s in variants)]
    assert len(set(scopes)) == len(scopes)


@pytest.mark.parametrize(
    'error,operation',
    [
        (TypeError, lambda: HTMLWriter(style='dark')),
        (TypeError, lambda: Style(theme=42)),
        (TypeError, lambda: Style(palette={})),
        (TypeError, lambda: Style(mode=None)),
        (ValueError, lambda: Style(theme='missing')),
        (ValueError, lambda: Style(palette='missing')),
        (ValueError, lambda: Style(mode='system')),
        (ValueError, lambda: HTMLWriter(style={'typo': 'slate'})),
        (ValueError, lambda: HTMLWriter(style={1: 'slate'})),
        (TypeError, lambda: Theme(name=42)),
        (ValueError, lambda: Theme(name=' ')),
        (TypeError, lambda: Palette(name=None)),
        (ValueError, lambda: Palette(name='')),
        (TypeError, lambda: Theme(name='custom', tokens=[])),
        (TypeError, lambda: Palette(name='custom', dark=None)),
        (ValueError, lambda: Theme(name='custom', tokens={'accent': 'red'})),
        (ValueError, lambda: Palette(name='custom', light={'font_size': '18px'})),
        (ValueError, lambda: Palette(name='custom', dark={'typo': 'red'})),
        (TypeError, lambda: Theme(name='custom', tokens={'font_size': 42})),
        (ValueError, lambda: Theme(name='custom', tokens={'font_size': ' '})),
        (TypeError, lambda: Palette(name='custom', light={'accent': 42})),
        (ValueError, lambda: Palette(name='custom', dark={'accent': ''})),
        (TypeError, lambda: Theme(name='custom', css=None)),
        (TypeError, lambda: get_theme([])),
        (TypeError, lambda: get_palette(None)),
    ],
)
def test_invalid_configuration(error, operation):
    with pytest.raises(error):
        operation()


def test_css_cannot_close_style_element(report):
    theme = Theme(name='custom', css='&::after { content: "</style>"; }')
    palette = Palette(name='custom', light={'accent': '</style>'})
    html = report.to_html(style=Style(theme=theme, palette=palette))
    assert html.count('</style>') == 1
    assert r'\3c /style>' in html


@pytest.mark.parametrize('name,mode', list(product(PALETTES, ('light', 'dark'))))
def test_palette_text_contrast(name, mode):
    def luminance(color):
        rgb = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [
            c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb
        ]
        return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    tokens = getattr(get_palette(name), mode)
    for fg, bg in product(
        ('text', 'heading', 'accent', 'accent_hover', 'description', 'muted'),
        ('page_background', 'background', 'surface', 'table_header'),
    ):
        hi, lo = sorted((luminance(tokens[fg]), luminance(tokens[bg])), reverse=True)
        assert (hi + 0.05) / (lo + 0.05) >= 4.5, (name, mode, fg, bg)


def test_explicit_styler_styles_survive_dark_mode(report):
    pd = pytest.importorskip('pandas')
    styler = pd.DataFrame({'Value': [1]}).style.set_properties(
        **{'color': '#123456', 'background-color': '#abcdef'}
    )
    report.add(styler, caption='Styled data')
    html = report.to_html(style={'mode': 'dark'})
    assert 'color: #123456;' in html
    assert 'background-color: #abcdef;' in html
    assert '<figcaption>Styled data</figcaption>' in html
    assert '!important' not in html

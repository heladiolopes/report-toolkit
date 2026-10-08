"""Artifact options through the public API, templates, and browser interactions."""

from html.parser import HTMLParser

import pytest

from report_toolkit import (
    AdapterRegistry,
    Artifact,
    HTMLWriter,
    RawHTML,
    RenderedArtifact,
    Report,
    TemplateError,
)


class Markup:
    def __init__(self, html):
        self.html = html


class MarkupAdapter:
    def render(self, value):
        return RenderedArtifact(value.html)


def writer(**options):
    registry = AdapterRegistry()
    registry.register(Markup, MarkupAdapter())
    return HTMLWriter(registry=registry, **options)


def box(width=160, height=100):
    return Markup(
        f'<div style="width:{width}px;height:{height}px;background:skyblue">Chart</div>'
    )


def test_options_templates_and_copy():
    value = box()
    report = Report()
    default = report.add(value)
    assert (default.width, default.center, default.expand) == (
        'native',
        True,
        'auto',
    )
    options = {
        'width': 'full',
        'center': True,
        'expand': 'always',
        'caption': 'A & B',
    }
    artifact = report.add(value, **options)
    copied = (report + Report()).document.children[1]
    assert copied is not artifact
    assert all(getattr(copied, key) == item for key, item in options.items())
    templated = Report.from_template_string(
        '{% artifact chart caption="A & B" expand="always" center=true width="full" %}',
        context={'chart': value},
    )
    assert all(
        getattr(templated.document.children[0], key) == item
        for key, item in options.items()
    )
    html = writer().render(templated.document)
    assert 'data-width="full" data-center="true" data-expand="always"' in html
    assert '<figcaption>A &amp; B</figcaption>' in html


@pytest.mark.parametrize(
    'options,error',
    [
        ({'width': 'auto'}, ValueError),
        ({'expand': True}, ValueError),
        ({'center': 1}, TypeError),
        ({'zoom': True}, TypeError),
    ],
)
def test_invalid_options(options, error):
    with pytest.raises(error):
        Report().add(box(), **options)
    with pytest.raises(error):
        Report().add('<b>HTML</b>', **options)


@pytest.mark.parametrize('center', [None, False])
def test_center_defaults_and_opt_out(center):
    value = box()
    options = {} if center is None else {'center': center}
    attribute = '' if center is None else ' center=false'
    report = Report()
    artifact = report.add(value, **options)
    templated = Report.from_template_string(
        '{% artifact chart' + attribute + ' %}', context={'chart': value}
    )
    expected = center is None
    assert Artifact(value, **options).center is expected
    assert artifact.center is expected
    assert templated.document.children[0].center is expected
    for document in (report.document, templated.document):
        assert f'data-center="{str(expected).lower()}"' in writer().render(document)


@pytest.mark.parametrize(
    'options',
    [{}, {'caption': None, 'width': 'native', 'center': True, 'expand': 'auto'}],
)
def test_raw_html_accepts_default_options(options):
    report = Report()
    payload = '<strong>trusted &amp; unchanged</strong>'
    node = report.add(payload, **options)
    assert isinstance(node, RawHTML)
    assert node.content == payload
    assert report.document.children == (node,)
    html = report.to_html(fragment=True)
    assert payload in html
    assert '<figure' not in html


def test_raw_html_and_pretty_validation():
    for options in (
        {'width': 'full'},
        {'center': False},
        {'expand': 'never'},
    ):
        with pytest.raises(ValueError, match='artifact options'):
            Report().add('<b>HTML</b>', **options)
    for pretty in (1, 'yes', None):
        with pytest.raises(TypeError, match='pretty'):
            Report().to_html(pretty=pretty)


@pytest.mark.parametrize(
    'attributes',
    [
        'width="bad"',
        'width="full" width="native"',
        'unknown=true',
        'zoom=true',
        'center=1',
        'expand=true',
        'caption=false',
    ],
)
def test_template_option_errors_have_lines(attributes):
    with pytest.raises(TemplateError, match='<template>:3:'):
        Report.from_template_string(
            '\n\n{% artifact chart ' + attributes + ' %}', context={'chart': box()}
        )


class Structure(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.events = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.events.append(('start', tag, attrs))

    def handle_endtag(self, tag):
        self.events.append(('end', tag))

    def handle_data(self, data):
        if data.strip():
            self.events.append(('data', data.strip()))


@pytest.mark.parametrize('fragment', [False, True])
def test_formatting_preserves_payloads_and_structure(tmp_path, fragment):
    payload = (
        '<pre>  leading\n\n  trailing  </pre><script>const value = " a  b ";\n</script>'
    )
    report = Report('Formatting')
    report.raw_html(payload)
    with report.columns(2), report.panel('Panel'):
        report.add(Markup(payload))
        report.markdown('```text\n  literal\n\n    spacing\n```')
    compact = writer().render(report.document, fragment=fragment)
    pretty = writer(pretty=True).render(report.document, fragment=fragment)
    assert compact.count(payload) == pretty.count(payload) == 2
    assert Structure(compact).events == Structure(pretty).events
    assert len(compact) < len(pretty)
    assert (
        '\n      <div class="report-panel">' in pretty
        if fragment
        else '\n          <div class="report-panel">' in pretty
    )
    path = writer(pretty=True).write(
        report.document, tmp_path / 'pretty.html', fragment=fragment
    )
    assert path.read_text() == pretty
    simple = Report('Simple')
    assert simple.write(
        tmp_path / 'simple.html', pretty=True
    ).read_text() == simple.to_html(pretty=True)


@pytest.fixture(scope='module')
def browser():
    playwright_api = pytest.importorskip('playwright.sync_api')
    sync_playwright = playwright_api.sync_playwright
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except playwright_api.Error as exc:
            pytest.skip(f'Chromium is unavailable: {exc}')
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    page = browser.new_page(viewport={'width': 1200, 'height': 900})
    yield page
    page.close()


def load(page, report, **options):
    page.set_content(writer(**options).render(report.document))
    page.wait_for_function("document.querySelector('.report-artifact-ready') !== null")


def test_center_expansion_and_restore(page):
    report = Report()
    report.add(box(), center=True, expand='always')
    report.add(box(1800, 1000))
    load(page, report)
    small = page.locator('figure.report-artifact').nth(0)
    viewport = small.locator('.report-artifact-viewport')
    before = viewport.bounding_box()
    content = small.locator('.report-artifact-content')
    bounds = content.bounding_box()
    assert (
        abs(bounds['x'] + bounds['width'] / 2 - before['x'] - before['width'] / 2) < 1
    )
    content.evaluate('(el) => el.savedState = 42')
    assert small.get_by_role('button').count() == 1
    assert small.locator('output').count() == 0
    small.get_by_role('button', name='Expand', exact=True).click()
    dialog = page.get_by_role('dialog')
    assert dialog.is_visible()
    assert (
        dialog.locator('.report-artifact-content').evaluate('(el) => el.savedState')
        == 42
    )
    assert dialog.get_by_role('button').count() == 4
    for label in ('Close', 'Zoom out', 'Zoom in', 'Reset'):
        assert (
            dialog.get_by_role('button', name=label, exact=True).locator('svg').count()
            == 1
        )
    assert dialog.locator('output').text_content() == '100%'
    preview_bounds = dialog.locator('.report-artifact-viewport').bounding_box()
    dialog.get_by_role('button', name='Zoom in', exact=True).click()
    page.wait_for_function("document.querySelector('dialog output').value === '125%'")
    assert dialog.locator('.report-artifact-viewport').bounding_box() == preview_bounds
    expanded = dialog.locator('.report-artifact-content').bounding_box()
    panel = dialog.locator('.report-artifact-viewport').bounding_box()
    assert expanded['width'] == pytest.approx(bounds['width'] * 1.25)
    assert expanded['height'] == pytest.approx(bounds['height'] * 1.25)
    for position, dimension in (('x', 'width'), ('y', 'height')):
        assert expanded[position] + expanded[dimension] / 2 == pytest.approx(
            panel[position] + panel[dimension] / 2, abs=1
        )
    page.keyboard.press('Escape')
    page.wait_for_function("!document.querySelector('dialog')")
    assert content.evaluate('(el) => el.savedState') == 42
    assert viewport.bounding_box() == before
    assert content.bounding_box() == bounds
    assert small.get_by_role('button').count() == 1
    assert small.get_by_role('button', name='Expand', exact=True).evaluate(
        '(el) => el === document.activeElement'
    )
    small.get_by_role('button', name='Expand', exact=True).click()
    assert dialog.locator('output').text_content() == '100%'
    assert dialog.locator('.report-artifact-content').bounding_box()[
        'width'
    ] == pytest.approx(bounds['width'])
    dialog.get_by_role('button', name='Zoom in', exact=True).click()
    page.wait_for_function("document.querySelector('dialog output').value === '125%'")
    dialog.get_by_role('button', name='Reset', exact=True).click()
    page.wait_for_function("document.querySelector('dialog output').value === '100%'")
    assert dialog.locator('.report-artifact-content').bounding_box()[
        'width'
    ] == pytest.approx(bounds['width'])
    dialog.get_by_role('button', name='Close', exact=True).click()
    page.wait_for_function("!document.querySelector('dialog')")
    large = page.locator('figure.report-artifact').nth(1)
    assert large.get_by_role('button', name='Expand', exact=True).is_visible()
    assert large.locator('.report-artifact-viewport').evaluate(
        '(el) => el.scrollWidth > el.clientWidth && el.scrollHeight <= el.clientHeight + 1'
    )


@pytest.mark.parametrize(('width', 'center'), [(160, True), (160, False), (1800, True)])
def test_expand_button_bottom_right_after_scroll_and_resize(page, width, center):
    report = Report()
    report.add(box(width, 200), center=center, expand='always')
    load(page, report)

    def assert_position():
        page.wait_for_function(
            """() => {
                const viewport = document.querySelector('figure .report-artifact-viewport').getBoundingClientRect();
                const space = document.querySelector('figure .report-artifact-space').getBoundingClientRect();
                const button = document.querySelector('figure .report-artifact-expand').getBoundingClientRect();
                return Math.abs(button.right - (Math.min(space.right, viewport.right) - 8)) < 1
                    && Math.abs(button.bottom - (Math.min(space.bottom, viewport.bottom) - 8)) < 1;
            }"""
        )

    assert_position()
    if width == 1800:
        page.locator('figure .report-artifact-viewport').evaluate(
            '(el) => el.scrollLeft = el.scrollWidth'
        )
        assert_position()
    page.set_viewport_size({'width': 390, 'height': 700})
    assert_position()


@pytest.mark.parametrize('javascript', [True, False])
@pytest.mark.parametrize('width', ['native', 'full'])
def test_tall_inline_artifact_has_no_height_limit(browser, width, javascript):
    page = browser.new_page(
        java_script_enabled=javascript, viewport={'width': 1200, 'height': 900}
    )
    try:
        report = Report()
        report.add(box(1600 if width == 'full' else 160, 2400), width=width)
        page.set_content(writer().render(report.document))
        if javascript:
            page.wait_for_function(
                "document.querySelector('.report-artifact-ready') !== null"
            )
        viewport = page.locator('figure .report-artifact-viewport')
        content = page.locator('figure .report-artifact-content')
        assert viewport.bounding_box()['height'] > 900
        assert viewport.bounding_box()['height'] == pytest.approx(
            content.bounding_box()['height'], abs=1
        )
        assert viewport.evaluate('(el) => el.scrollHeight <= el.clientHeight + 1')
        assert page.get_by_role('button', name='Expand', exact=True).count() == 0
        if javascript:
            page.set_viewport_size({'width': 390, 'height': 700})
            page.wait_for_function(
                """() => {
                    const viewport = document.querySelector('figure .report-artifact-viewport');
                    const content = document.querySelector('figure .report-artifact-content');
                    return Math.abs(viewport.getBoundingClientRect().height - content.getBoundingClientRect().height) < 1
                        && viewport.scrollHeight <= viewport.clientHeight + 1;
                }"""
            )
    finally:
        page.close()


def test_async_overflow_fragments_and_mobile(page):
    report = Report()
    report.add(box())
    html = writer().render(report.document, fragment=True)
    page.set_content(html + html)
    page.wait_for_function(
        "document.querySelectorAll('.report-artifact-ready').length === 2"
    )
    assert page.get_by_role('button', name='Expand', exact=True).count() == 0
    assert page.locator('figure .report-artifact-expand').count() == 2
    first = page.locator('figure').first
    first.locator('.report-artifact-content > div').evaluate(
        '(el) => el.style.width = "1800px"'
    )
    first.get_by_role('button', name='Expand', exact=True).wait_for(state='visible')
    page.set_viewport_size({'width': 390, 'height': 700})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert first.locator('.report-artifact-viewport').evaluate(
        '(el) => el.scrollWidth > el.clientWidth'
    )


def test_table_native_full_and_no_javascript(browser, page):
    pd = pytest.importorskip('pandas')
    report = Report()
    frame = pd.DataFrame({'A': [1, 2]})
    report.add(frame, center=True)
    report.add(frame, width='full')
    for enabled in (True, False):
        target = (
            page
            if enabled
            else browser.new_page(
                java_script_enabled=False, viewport={'width': 1200, 'height': 900}
            )
        )
        try:
            target.set_content(report.to_html())
            if enabled:
                target.wait_for_function(
                    "document.querySelectorAll('.report-artifact-ready').length === 2"
                )
            artifacts = target.locator('figure')
            native = artifacts.nth(0).locator('table').bounding_box()
            full = artifacts.nth(1).locator('table').bounding_box()
            viewport = (
                artifacts.nth(1).locator('.report-artifact-viewport').bounding_box()
            )
            assert native['width'] < full['width'] / 2
            assert full['width'] == pytest.approx(viewport['width'], abs=1)
            if enabled:
                assert full['width'] / full['height'] == pytest.approx(
                    native['width'] / native['height'], abs=0.01
                )
            assert target.get_by_role('button', name='Expand', exact=True).count() == 0
        finally:
            if not enabled:
                target.close()


def test_print_hides_expansion_and_preserves_content(page):
    report = Report()
    report.add(box(), width='full', expand='always')
    load(page, report)
    page.emulate_media(media='print')
    assert page.locator('.report-artifact-expand').is_hidden()
    assert (
        page.locator('.report-artifact-content').evaluate(
            '(el) => getComputedStyle(el).transform'
        )
        == 'none'
    )
    assert (
        page.locator('.report-artifact-content').evaluate(
            '(el) => getComputedStyle(el).position'
        )
        == 'static'
    )


def assert_proportional_fit(page, selector, ratio):
    page.wait_for_function(
        """({selector, ratio}) => {
            const content = document.querySelector(selector);
            const viewport = content.closest('.report-artifact-viewport');
            const bounds = content.getBoundingClientRect();
            return Math.abs(bounds.width - viewport.clientWidth) < 1
                && Math.abs(bounds.width / bounds.height - ratio) < .01;
        }""",
        arg={'selector': selector, 'ratio': ratio},
    )


def assert_native_size(page, selector, width, height):
    page.wait_for_function(
        """({selector, width, height}) => {
            const bounds = document.querySelector(selector).getBoundingClientRect();
            return Math.abs(bounds.width - width) < 1
                && Math.abs(bounds.height - height) < 1;
        }""",
        arg={'selector': selector, 'width': width, 'height': height},
    )


def test_plotly_full_width_resize_and_state(page):
    go = pytest.importorskip('plotly.graph_objects')
    from plotly.offline import get_plotlyjs

    page.route(
        'https://cdn.plot.ly/**',
        lambda route: route.fulfill(
            body=get_plotlyjs(), content_type='application/javascript'
        ),
    )
    report = Report()
    chart = go.Figure(go.Bar(x=['A', 'B'], y=[1, 2]))
    chart.update_layout(width=320, height=240)
    report.add(chart, width='full', expand='always')
    report.add(chart)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_content(report.to_html())
    inline = 'figure .report-artifact-content'
    expanded = 'dialog .report-artifact-content'
    assert_proportional_fit(page, inline, 320 / 240)
    first = page.locator('figure').first
    assert first.locator('.js-plotly-plot').evaluate(
        '(el) => [el._fullLayout.width, el._fullLayout.height]'
    ) == [320, 240]
    first.get_by_role('button', name='Expand', exact=True).click()
    assert_native_size(page, expanded, 320, 240)
    page.get_by_role('dialog').get_by_role('button', name='Close', exact=True).click()
    page.wait_for_function("!document.querySelector('dialog')")
    assert_proportional_fit(page, inline, 320 / 240)
    page.set_viewport_size({'width': 390, 'height': 700})
    assert_proportional_fit(page, inline, 320 / 240)
    assert not errors


def test_altair_full_width_and_multiple_offline_charts(page):
    alt = pytest.importorskip('altair')
    pytest.importorskip('vl_convert')
    report = Report()
    chart = (
        alt.Chart(alt.Data(values=[{'x': 1, 'y': 2}]))
        .mark_point()
        .encode(x='x:Q', y='y:Q')
        .properties(width=200, height=150)
    )
    report.add(chart, width='full', expand='always')
    report.add(chart)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_content(HTMLWriter(inline_altair=True).render(report.document))
    page.wait_for_function(
        "Array.from(document.querySelectorAll('[id^=reporttkt_chart_]')).filter(el => el.reporttktView).length === 2"
    )
    native = (
        page.locator('figure').nth(1).locator('.report-artifact-content').bounding_box()
    )
    ratio = native['width'] / native['height']
    assert_proportional_fit(page, 'figure .report-artifact-content', ratio)
    first = page.locator('figure').first
    assert first.locator('[id^=reporttkt_chart_]').evaluate(
        '(el) => [el.reporttktView.width(), el.reporttktView.height()]'
    ) == [200, 150]
    first.get_by_role('button', name='Expand', exact=True).click()
    assert_native_size(
        page, 'dialog .report-artifact-content', native['width'], native['height']
    )
    page.keyboard.press('Escape')
    page.wait_for_function("!document.querySelector('dialog')")
    page.set_viewport_size({'width': 390, 'height': 700})
    assert_proportional_fit(page, 'figure .report-artifact-content', ratio)
    assert not errors


@pytest.mark.parametrize('hover_before_expansion', [False, True])
def test_altair_tooltips_in_expanded_mode(page, hover_before_expansion):
    alt = pytest.importorskip('altair')
    pytest.importorskip('vl_convert')
    report = Report()
    for label in ('First chart', 'Second chart'):
        chart = (
            alt.Chart(alt.Data(values=[{'x': 1, 'y': 2, 'label': label}]))
            .mark_circle(size=400)
            .encode(
                x='x:Q',
                y='y:Q',
                tooltip=[alt.Tooltip('label:N', title='title'), 'x:Q'],
            )
            .properties(
                width=200,
                height=150,
                usermeta={
                    'embedOptions': {
                        'renderer': 'svg',
                        'actions': False,
                        'tooltip': {
                            'theme': 'light' if label == 'First chart' else 'dark'
                        },
                    }
                },
            )
        )
        report.add(chart, expand='always')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_content(HTMLWriter(inline_altair=True).render(report.document))
    page.wait_for_function(
        "Array.from(document.querySelectorAll('[id^=reporttkt_chart_]')).filter(el => el.reporttktView).length === 2"
    )

    def hover_and_check(host, label):
        host.locator('.mark-symbol path').hover()
        tooltip = page.locator('.vg-tooltip.visible')
        tooltip.wait_for(state='visible')
        assert label in tooltip.inner_text()
        # Visibility alone does not detect a tooltip behind the modal's backdrop.
        assert tooltip.evaluate(
            """el => {
                const original = el.style.pointerEvents;
                el.style.pointerEvents = 'auto';
                try {
                    const bounds = el.getBoundingClientRect();
                    return el.contains(document.elementFromPoint(
                        bounds.x + bounds.width / 2, bounds.y + bounds.height / 2
                    ));
                } finally {
                    el.style.pointerEvents = original;
                }
            }"""
        )
        return {
            **tooltip.bounding_box(),
            'styles': tooltip.evaluate(
                """el => [el, ...el.querySelectorAll('*')].map(node => {
                    const style = getComputedStyle(node);
                    return Object.fromEntries([
                        'fontFamily', 'fontSize', 'fontWeight', 'lineHeight',
                        'color', 'backgroundColor', 'padding', 'border',
                        'borderCollapse', 'borderSpacing', 'boxSizing'
                    ].map(property => [property, style[property]]));
                })"""
            ),
        }

    for index, label in enumerate(('First chart', 'Second chart')):
        figure = page.locator('figure').nth(index)
        if hover_before_expansion:
            hover_and_check(figure, label)
        figure.get_by_role('button', name='Expand', exact=True).click()
        dialog = page.get_by_role('dialog')
        original = hover_and_check(dialog, label)
        assert dialog.locator('.vg-tooltip.visible').count() == 1
        dialog.get_by_role('button', name='Zoom in', exact=True).click()
        page.wait_for_function(
            "document.querySelector('dialog output').value === '125%'"
        )
        zoomed = hover_and_check(dialog, label)
        assert zoomed['width'] == pytest.approx(original['width'])
        assert zoomed['height'] == pytest.approx(original['height'])
        if index == 0:
            page.keyboard.press('Escape')
        else:
            dialog.get_by_role('button', name='Close', exact=True).click()
        page.wait_for_function("!document.querySelector('dialog')")
        assert page.locator('body > .vg-tooltip').count() == 1
        assert page.locator('.vg-tooltip.visible').count() == 0
        inline = hover_and_check(figure, label)
        assert inline['styles'] == original['styles']
        assert inline['width'] == pytest.approx(original['width'])
        assert inline['height'] == pytest.approx(original['height'])
        figure.get_by_role('button', name='Expand', exact=True).click()
        hover_and_check(page.get_by_role('dialog'), label)
        page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
        assert page.locator('dialog').count() == 0
        assert page.locator('body > .vg-tooltip').count() == 1
        assert page.locator('.vg-tooltip.visible').count() == 0
        page.evaluate("window.dispatchEvent(new Event('afterprint'))")
        hover_and_check(figure, label)
    assert not errors


def test_pretty_keeps_adjacent_inline_payloads_adjacent():
    report = Report()
    report.raw_html('<span>one</span>')
    report.raw_html('<span>two</span>')
    for pretty in (False, True):
        assert '<span>one</span><span>two</span>' in report.to_html(pretty=pretty)


def test_matplotlib_full_width_preserves_aspect_ratio(page):
    Figure = pytest.importorskip('matplotlib.figure').Figure
    report = Report()
    chart = Figure(figsize=(2, 1))
    chart.subplots().plot([1, 2])
    report.add(chart, center=True)
    report.add(chart, width='full')
    page.set_content(report.to_html())
    page.wait_for_function(
        'Array.from(document.images).every(img => img.complete && img.naturalWidth)'
    )
    page.wait_for_function(
        "document.querySelectorAll('.report-artifact-ready').length === 2"
    )
    images = page.locator('.reporttkt-figure-image')
    native, full = [images.nth(i).bounding_box() for i in range(2)]
    assert full['width'] > native['width']
    assert full['width'] / full['height'] == pytest.approx(
        native['width'] / native['height'], abs=0.01
    )


def test_dialog_focus_containment_and_print_restores_content(page):
    report = Report()
    report.add(box(), expand='always')
    load(page, report)
    page.get_by_role('button', name='Expand', exact=True).click()
    for _ in range(8):
        page.keyboard.press('Tab')
        assert page.evaluate("!!document.activeElement.closest('dialog')")
    page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
    assert page.locator('dialog').count() == 0
    assert page.locator('figure .report-artifact-content').count() == 1
    page.evaluate("window.dispatchEvent(new Event('afterprint'))")


@pytest.mark.parametrize(('width', 'height'), [(160, 100), (1600, 800)])
def test_full_width_custom_artifact_preserves_proportions(page, width, height):
    report = Report()
    report.add(box(width, height), width='full', expand='always')
    load(page, report)
    ratio = width / height
    assert_proportional_fit(page, 'figure .report-artifact-content', ratio)
    viewport = page.locator('figure .report-artifact-viewport')
    assert viewport.evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
    page.get_by_role('button', name='Expand', exact=True).click()
    expanded = 'dialog .report-artifact-content'
    dialog = page.get_by_role('dialog')
    assert_native_size(page, expanded, width, height)
    assert dialog.locator('output').text_content() == '100%'
    page.set_viewport_size({'width': 390, 'height': 700})
    assert_native_size(page, expanded, width, height)
    dialog.get_by_role('button', name='Zoom in', exact=True).click()
    assert_native_size(page, expanded, width * 1.25, height * 1.25)
    dialog.get_by_role('button', name='Reset', exact=True).click()
    assert_native_size(page, expanded, width, height)
    dialog.get_by_role('button', name='Zoom out', exact=True).click()
    assert_native_size(page, expanded, width * 0.75, height * 0.75)
    page.keyboard.press('Escape')
    page.wait_for_function("!document.querySelector('dialog')")
    assert_proportional_fit(page, 'figure .report-artifact-content', ratio)
    page.get_by_role('button', name='Expand', exact=True).click()
    assert_native_size(page, expanded, width, height)
    assert dialog.locator('output').text_content() == '100%'

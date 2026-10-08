"""Reader mode's public contract and optional browser regressions."""

import re

import pytest

from report_toolkit import HTMLWriter, Report, get_profile


def reader_report():
    report = Report('Reader title')
    for level, label in [(1, 'Parent'), (2, 'Child'), (4, 'Deep'), (1, 'End')]:
        report.heading(level, label)
        report.paragraph('Reflowing article content. ' * 40)
        report.raw_html('<div style="height:1000px">Content</div>')
    return report


def test_reader_forwarding_and_empty_toc(tmp_path):
    report = reader_report()
    options = {'toc': True, 'toc_position': 'reader', 'toc_depth': 2}
    html = report.to_html(**options)
    assert html == HTMLWriter(**options).render(report.document)
    assert report.write(tmp_path / 'reader.html', **options).read_text() == html
    assert html == report.to_html(**options)
    assert re.findall(r'<h[1-6] id="([^"]+)"', html) == re.findall(
        r'<h[1-6] id="([^"]+)"', report.to_html()
    )
    assert 'data-reader-icon="moon"' in html
    assert 'data-reader-icon="sun"' in html
    assert 'data-reader-icon="menu"' in html
    assert 'role="tooltip" hidden>Switch to dark mode</span>' in html
    assert 'aria-label="Switch to dark mode"' in html
    assert html.index('class="report-reader-bar"') < html.index('<article')
    assert '<h1 class="report-title">Reader title</h1>' in html
    for empty in (Report(), Report('Only title')):
        rendered = empty.to_html(**options)
        assert '<button class="report-reader-toggle"' not in rendered
        assert '<div class="report-sidebar"' not in rendered
        assert '<button class="report-theme-toggle"' in rendered
        assert '<script>' in rendered
    assert 'report-reader-title">Report</div>' in Report().to_html(**options)


def test_reader_eligibility():
    with pytest.raises(ValueError, match='toc=True'):
        HTMLWriter(toc_position='reader')
    with pytest.raises(ValueError, match='fragments'):
        Report().to_html(toc=True, toc_position='reader', fragment=True)
    for profile in ('portable', 'content'):
        with pytest.raises(ValueError, match='positioning'):
            Report().to_html(toc=True, toc_position='reader', profile=profile)
    for overrides in (
        {'content_only': True},
        {'stylesheet': 'layout'},
        {'chart_mode': 'svg', 'artifact_controls': False},
    ):
        profile = get_profile('rich').with_overrides(name='custom', **overrides)
        with pytest.raises(ValueError, match='themed interactive full-page'):
            HTMLWriter(toc=True, toc_position='reader', profile=profile)
    assert get_profile('rich').toc_positions == ('top', 'sidebar', 'reader')
    assert get_profile('portable').toc_positions == ('top', 'sidebar')


@pytest.fixture
def browser():
    playwright = pytest.importorskip('playwright.sync_api')
    with playwright.sync_playwright() as runtime:
        try:
            browser = runtime.chromium.launch()
        except playwright.Error as exc:
            pytest.skip(f'Chromium unavailable: {exc}')
        yield browser
        browser.close()


def test_reader_desktop_tracking_reflow_theme_and_print(browser, tmp_path):
    page = browser.new_page(viewport={'width': 1440, 'height': 800})
    errors = []
    page.on('pageerror', lambda error: errors.append(error))
    page.set_content(
        reader_report().to_html(
            toc=True, toc_position='reader', collapsible_toc=True, toc_depth=2
        )
    )
    page.locator('#reporttkt-deep').evaluate('(heading) => heading.scrollIntoView()')
    page.wait_for_timeout(100)
    assert page.locator('.report-breadcrumbs a').all_text_contents() == [
        'Parent',
        'Child',
        'Deep',
    ]
    assert page.locator('.report-toc a[aria-current]').inner_text() == 'Child'
    top = page.locator('#reporttkt-deep').bounding_box()['y']
    assert top == pytest.approx(
        page.locator('.report-reader-bar').bounding_box()['height'] + 24, abs=1
    )
    page.locator('.report-reader-toggle').click()
    page.wait_for_timeout(100)
    assert not page.locator('.report-sidebar').is_visible()
    assert page.locator('#reporttkt-deep').bounding_box()['y'] == pytest.approx(
        top, abs=2
    )
    page.locator('.report-reader-toggle').click()
    page.locator('.report-theme-toggle').click()
    assert page.locator('.report-reader').get_attribute('data-reader-theme') == 'dark'
    page.locator('.report-breadcrumbs a').first.click()
    assert page.locator('#reporttkt-parent').evaluate(
        '(el) => el === document.activeElement'
    )
    page.evaluate("location.hash = '#reporttkt-deep'")
    page.wait_for_timeout(100)
    assert page.locator('#reporttkt-deep').bounding_box()['y'] == pytest.approx(
        top, abs=2
    )
    page.locator('.report-toc-toggle').first.click()
    assert page.locator('.report-toc ul[hidden]').count() == 1
    page.locator('.report-reader-toggle').click()
    page.emulate_media(media='print')
    assert page.locator('.report-sidebar').is_visible()
    assert not page.locator('.report-reader-bar').is_visible()
    assert page.locator('.report-toc ul[hidden]').first.is_visible()
    assert (
        page.locator('.report-toc').evaluate('(el) => getComputedStyle(el).maxHeight')
        == 'none'
    )
    assert (
        page.locator('.report-sidebar').evaluate(
            '(el) => getComputedStyle(el).overflow'
        )
        == 'visible'
    )
    page.emulate_media(media='screen')
    assert not page.locator('.report-sidebar').is_visible()
    page.set_viewport_size({'width': 1200, 'height': 700})
    assert not page.locator('.report-sidebar').is_visible()
    path = tmp_path / 'reader.html'
    path.write_text(
        reader_report().to_html(
            toc=True, toc_position='reader', collapsible_toc=True, toc_depth=2
        )
    )
    page.goto(path.as_uri() + '#reporttkt-deep')
    page.wait_for_timeout(100)
    assert page.locator('#reporttkt-deep').bounding_box()['y'] == pytest.approx(
        page.locator('.report-reader-bar').bounding_box()['height'] + 24, abs=1
    )
    assert page.locator('.report-breadcrumbs a[aria-current]').inner_text() == 'Deep'
    assert not errors
    page.close()


def test_reader_mobile_focus_breakpoints_and_fallback(browser):
    html = reader_report().to_html(toc=True, toc_position='reader', toc_depth=2)
    page = browser.new_page(viewport={'width': 500, 'height': 700})
    page.set_content(html)
    toggle = page.locator('.report-reader-toggle')
    assert not page.locator('.report-sidebar').is_visible()
    toggle.click()
    close = page.locator('.report-reader-close')
    assert close.evaluate('(el) => el === document.activeElement')
    page.keyboard.press('Shift+Tab')
    assert page.locator('.report-toc a').last.evaluate(
        '(el) => el === document.activeElement'
    )
    page.keyboard.press('Tab')
    assert close.evaluate('(el) => el === document.activeElement')
    page.keyboard.press('Escape')
    assert toggle.evaluate('(el) => el === document.activeElement')
    assert page.evaluate('document.body.style.overflow') == ''
    toggle.click()
    page.locator('.report-toc a').first.click()
    assert not page.locator('.report-sidebar').is_visible()
    assert page.locator('#reporttkt-parent').evaluate(
        '(el) => el === document.activeElement'
    )
    toggle.click()
    page.locator('.report-reader-backdrop').click(position={'x': 450, 'y': 100})
    assert not page.locator('.report-sidebar').is_visible()
    toggle.click()
    page.set_viewport_size({'width': 1440, 'height': 800})
    page.wait_for_timeout(100)
    assert page.evaluate('document.body.style.overflow') == ''
    assert page.locator('.report-sidebar').is_visible()
    toggle.click()
    page.set_viewport_size({'width': 500, 'height': 700})
    page.set_viewport_size({'width': 1440, 'height': 800})
    page.wait_for_timeout(100)
    assert not page.locator('.report-sidebar').is_visible()
    page.close()
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.set_content(html)
    assert not page.locator('.report-reader-bar').is_visible()
    assert page.locator('.report-sidebar').is_visible()
    assert page.locator('.report-toc ul[hidden]').count() == 0
    assert not page.locator('.report-reader-collapse').is_visible()
    context.close()


def test_reader_auto_and_empty_navigation(browser):
    page = browser.new_page()
    page.emulate_media(color_scheme='dark')
    page.set_content(
        Report().to_html(toc=True, toc_position='reader', style={'mode': 'auto'})
    )
    assert page.locator('.report-reader').get_attribute('data-reader-theme') == 'dark'
    assert page.locator('.report-theme-toggle [data-reader-icon="sun"]').is_visible()
    assert (
        page.locator('.report-theme-toggle').get_attribute('aria-label')
        == 'Switch to light mode'
    )
    page.emulate_media(color_scheme='light')
    page.wait_for_timeout(100)
    assert page.locator('.report-reader').get_attribute('data-reader-theme') == 'light'
    assert page.locator('.report-theme-toggle [data-reader-icon="moon"]').is_visible()
    assert (
        page.locator('.report-theme-toggle [role="tooltip"]').inner_text()
        == 'Switch to dark mode'
    )
    page.locator('.report-theme-toggle').click()
    page.emulate_media(color_scheme='dark')
    page.emulate_media(color_scheme='light')
    page.wait_for_timeout(100)
    assert page.locator('.report-reader').get_attribute('data-reader-theme') == 'dark'
    page.close()


def test_reader_theme_colors_and_embedded_styles(browser):
    report = Report('Colors')
    report.heading(1, 'Section')
    report.raw_html(
        '<table><thead><tr><th>Header</th></tr></thead>'
        '<tbody><tr><td>Value</td></tr></tbody></table>'
        '<div id="explicit" style="color:rgb(1,2,3);background:rgb(4,5,6)">Styled</div>'
    )
    page = browser.new_page()
    page.set_content(report.to_html(toc=True, toc_position='reader'))

    def colors():
        return page.evaluate("""() => [
        getComputedStyle(document.body).backgroundColor,
        getComputedStyle(document.querySelector('article')).backgroundColor,
        getComputedStyle(document.querySelector('th')).backgroundColor,
        getComputedStyle(document.querySelector('.report-reader-bar')).backgroundColor
    ]""")

    light = colors()
    page.locator('.report-theme-toggle').click()
    assert all(before != after for before, after in zip(light, colors(), strict=True))
    assert (
        page.locator('#explicit').evaluate('(el) => getComputedStyle(el).color')
        == 'rgb(1, 2, 3)'
    )
    page.close()


def test_reader_control_styles_tooltips_and_theme_icons(browser):
    page = browser.new_page(viewport={'width': 1440, 'height': 800})
    page.set_content(reader_report().to_html(toc=True, toc_position='reader'))
    theme = page.locator('.report-theme-toggle')
    toggle = page.locator('.report-reader-toggle')
    tooltip = theme.locator('[role="tooltip"]')
    assert theme.locator('[data-reader-icon="moon"]').is_visible()
    assert not theme.locator('[data-reader-icon="sun"]').is_visible()
    assert not tooltip.is_visible()
    assert not page.locator('.report-reader-close').is_visible()
    assert theme.evaluate('(el) => getComputedStyle(el).borderTopWidth') == '0px'
    assert (
        theme.evaluate('(el) => getComputedStyle(el).backgroundColor')
        == 'rgba(0, 0, 0, 0)'
    )
    for control in (theme, toggle):
        box = control.bounding_box()
        assert box['width'] == box['height'] == 40
        assert control.locator('svg:not([hidden])').bounding_box()['width'] == 20
    theme.hover()
    assert tooltip.is_visible()
    assert tooltip.inner_text() == 'Switch to dark mode'
    page.keyboard.press('Escape')
    assert not tooltip.is_visible()
    page.mouse.move(0, 200)
    theme.hover()
    assert tooltip.is_visible()
    page.wait_for_timeout(200)
    hover_background = theme.evaluate('(el) => getComputedStyle(el).backgroundColor')
    assert hover_background != 'rgba(0, 0, 0, 0)'
    page.wait_for_timeout(200)
    page.mouse.down()
    assert not tooltip.is_visible()
    page.wait_for_timeout(200)
    assert (
        theme.evaluate('(el) => getComputedStyle(el).backgroundColor')
        != hover_background
    )
    page.mouse.up()
    assert theme.get_attribute('aria-label') == 'Switch to light mode'
    assert tooltip.inner_text() == 'Switch to light mode'
    assert theme.locator('[data-reader-icon="sun"]').is_visible()
    assert not theme.locator('[data-reader-icon="moon"]').is_visible()
    assert not tooltip.is_visible()
    page.mouse.move(0, 200)
    theme.blur()
    theme.focus()
    page.keyboard.press('Shift+Tab')
    page.keyboard.press('Tab')
    assert tooltip.is_visible()
    assert theme.evaluate('(el) => getComputedStyle(el).outlineStyle') == 'solid'
    page.keyboard.press('Escape')
    assert not tooltip.is_visible()
    theme.blur()
    theme.focus()
    assert tooltip.is_visible()
    box = tooltip.bounding_box()
    assert box['x'] >= 0 and box['x'] + box['width'] <= 1440
    page.emulate_media(media='print')
    assert not tooltip.is_visible()
    page.emulate_media(media='screen')
    toggle.click()
    assert toggle.get_attribute('aria-label') == 'Show table of contents'
    assert toggle.locator('[role="tooltip"]').inner_text() == 'Show table of contents'
    page.close()


def test_reader_long_breadcrumbs_preserve_controls_and_current_section(browser):
    report = Report('A very long report title ' * 20)
    labels = [f'Level {level}: ' + 'Long section label ' * 15 for level in range(1, 7)]
    for level, label in enumerate(labels, 1):
        report.heading(level, label)
        report.raw_html('<div style="height:900px">Content</div>')
    page = browser.new_page(viewport={'width': 1100, 'height': 800})
    page.set_content(report.to_html(toc=True, toc_position='reader', toc_depth=2))
    page.locator('[data-reporttkt-heading="6"]').evaluate('(el) => el.scrollIntoView()')
    page.wait_for_timeout(100)
    crumbs = page.locator('.report-breadcrumbs a')
    assert crumbs.all_text_contents() == labels
    assert crumbs.last.get_attribute('aria-current') == 'location'
    assert crumbs.nth(2).get_attribute('title') == labels[2]
    assert (
        crumbs.nth(2)
        .locator('span')
        .evaluate('(el) => el.scrollWidth > el.clientWidth')
    )
    current_width = crumbs.last.bounding_box()['width']
    assert (
        current_width
        >= page.locator('.report-breadcrumbs').bounding_box()['width'] * 0.4 - 0.5
    )
    for width in (1100, 1440, 500, 320):
        page.set_viewport_size({'width': width, 'height': 800})
        page.wait_for_timeout(100)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        for name in ('.report-reader-toggle', '.report-theme-toggle'):
            box = page.locator(name).bounding_box()
            assert box['width'] == 40
            assert box['x'] >= 0 and box['x'] + box['width'] <= width
        assert crumbs.last.is_visible()
        if width < 1100:
            assert not crumbs.first.is_visible()
        title = page.locator('.report-reader-title')
        assert float(
            title.evaluate('(el) => getComputedStyle(el).fontSize').rstrip('px')
        ) > float(
            crumbs.last.evaluate('(el) => getComputedStyle(el).fontSize').rstrip('px')
        )
        assert title.evaluate(
            '(el) => getComputedStyle(el).color'
        ) != crumbs.last.evaluate('(el) => getComputedStyle(el).color')
    page.close()


def test_reader_tooltips_do_not_open_on_touch(browser):
    context = browser.new_context(
        viewport={'width': 390, 'height': 800}, has_touch=True, is_mobile=True
    )
    page = context.new_page()
    page.set_content(reader_report().to_html(toc=True, toc_position='reader'))
    page.locator('.report-theme-toggle').tap()
    assert not page.locator('.report-theme-toggle [role="tooltip"]').is_visible()
    assert page.locator('.report-theme-toggle [data-reader-icon="sun"]').is_visible()
    page.locator('.report-reader-toggle').tap()
    assert not page.locator('.report-reader-close [role="tooltip"]').is_visible()
    context.close()


def test_reader_header_and_rendered_depth_contract():
    report = reader_report()
    html = report.to_html(toc=True, toc_position='reader', collapsible_toc=True)
    nav = html.split('<nav data-reporttkt-navigation=', 1)[1].split('</nav>', 1)[0]
    assert 'class="report-reader-toc-header"' in nav
    assert 'aria-label="Collapse all sections"' in nav
    assert 'role="tooltip" hidden>Collapse all sections</span>' in nav
    assert 'class="report-reader-close"' in nav
    assert re.findall(r'--reporttkt-toc-indent: ([^"]+)', nav) == [
        '0rem',
        '0.75rem',
        '1.5rem',
        '0rem',
    ]
    profile = get_profile('rich').with_overrides(
        name='untitled', include_toc_title=False
    )
    untitled = report.to_html(
        toc=True, toc_position='reader', collapsible_toc=True, profile=profile
    )
    assert '<div class="report-toc-title">' not in untitled
    assert '<button class="report-reader-collapse"' in untitled
    flat = Report()
    flat.heading(1, 'Only section')
    for document, options in (
        (flat, {}),
        (Report(), {}),
        (report, {'collapsible_toc': False}),
    ):
        assert '<button class="report-reader-collapse"' not in document.to_html(
            toc=True, toc_position='reader', **options
        )
    for position in ('top', 'sidebar'):
        rendered = report.to_html(toc=True, toc_position=position, collapsible_toc=True)
        assert '<div class="report-reader-toc-header"' not in rendered
        assert '--reporttkt-toc-indent:' not in rendered
        assert '<span aria-hidden="true">⌄</span>' in rendered


def test_reader_collapse_precedence_and_centering(browser):
    page = browser.new_page(viewport={'width': 1440, 'height': 800})
    page.set_content(
        reader_report().to_html(toc=True, toc_position='reader', collapsible_toc=True)
    )
    page.locator('#reporttkt-deep').evaluate('(el) => el.scrollIntoView()')
    page.wait_for_timeout(100)
    collapse = page.locator('.report-reader-collapse')
    position = page.evaluate('scrollY')
    heading = page.locator('.report-toc a[aria-current]').inner_text()
    crumbs = page.locator('.report-breadcrumbs').inner_text()
    collapse.click()
    assert collapse.evaluate('(el) => el === document.activeElement')
    assert page.evaluate('scrollY') == position
    assert page.evaluate('location.hash') == ''
    assert page.locator('.report-toc a[aria-current]').inner_text() == heading
    assert page.locator('.report-breadcrumbs').inner_text() == crumbs
    assert page.locator('.report-toc-toggle[aria-expanded="true"]').count() == 0
    assert page.locator('.report-toc a[data-reader-ancestor]').count() == 2
    page.locator('#reporttkt-child').evaluate('(el) => el.scrollIntoView()')
    page.wait_for_timeout(100)
    assert page.locator('.report-toc a[aria-current]').inner_text() == 'Child'
    assert page.locator('.report-toc-toggle[aria-expanded="true"]').count() == 0
    page.locator('.report-breadcrumbs a').first.click()
    page.evaluate("location.hash = '#reporttkt-deep'")
    page.wait_for_timeout(100)
    assert page.locator('.report-toc-toggle[aria-expanded="true"]').count() == 0
    for width in (1440, 1200, 1100):
        top = page.locator('#reporttkt-deep').bounding_box()['y']
        page.set_viewport_size({'width': width, 'height': 800})
        page.wait_for_timeout(100)
        assert page.locator('#reporttkt-deep').bounding_box()['y'] == pytest.approx(
            top, abs=2
        )
        padding = page.locator('article').evaluate(
            '(el) => getComputedStyle(el).padding'
        )
        for hidden in (False, True):
            if hidden:
                page.locator('.report-reader-toggle').click()
            page.wait_for_timeout(100)
            box = page.locator('.report-reader').bounding_box()
            assert box['x'] + box['width'] / 2 == pytest.approx(width / 2, abs=1)
            assert (
                page.locator('article').evaluate('(el) => getComputedStyle(el).padding')
                == padding
            )
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            if hidden:
                assert box['width'] <= page.locator('.report-reader').evaluate(
                    '(el) => parseFloat(getComputedStyle(el).maxWidth)'
                )
                page.locator('.report-reader-toggle').click()
                page.wait_for_timeout(100)
    page.set_viewport_size({'width': 500, 'height': 800})
    page.locator('.report-reader-toggle').click()
    collapse.focus()
    assert collapse.locator('[role="tooltip"]').is_visible()
    page.emulate_media(media='print')
    assert not collapse.is_visible()
    assert page.locator('.report-toc ul[hidden]').first.is_visible()
    assert (
        page.locator('.report-toc').evaluate('(el) => getComputedStyle(el).maxHeight')
        == 'none'
    )
    assert (
        page.locator('.report-sidebar').evaluate(
            '(el) => getComputedStyle(el).overflow'
        )
        == 'visible'
    )
    page.emulate_media(media='screen')
    assert page.locator('.report-toc-toggle[aria-expanded="true"]').count() == 0
    page.locator('.report-toc-toggle').first.click()
    page.locator('.report-toc a').filter(has_text='Child').click()
    assert page.locator('.report-toc-toggle[aria-expanded="true"]').count() == 2
    page.close()


@pytest.mark.parametrize('levels', [(1, 2, 3, 4, 5, 6), (1, 3, 6)])
def test_reader_hierarchy_styles_and_sticky_scroll(browser, levels):
    report = Report('Hierarchy')
    for level in levels:
        report.heading(level, f'Level {level} ' + 'long wrapped label ' * 8)
        report.raw_html('<div style="height:900px">Content</div>')
    for index in range(30):
        report.heading(1, f'Other {index}')
        report.paragraph('Content')
    page = browser.new_page(viewport={'width': 1440, 'height': 800})
    page.set_content(
        report.to_html(
            toc=True,
            toc_position='reader',
            collapsible_toc=True,
            numbered_headings=True,
        )
    )
    page.locator(f'[data-reporttkt-heading="{levels[-1]}"]').first.evaluate(
        '(el) => el.scrollIntoView()'
    )
    page.wait_for_timeout(100)
    links = page.locator('.report-toc a')
    assert links.first.inner_text().startswith('1. ')
    assert links.nth(1).inner_text().startswith('1.1. ')
    for index in range(len(levels)):
        link = links.nth(index)
        assert (
            link.evaluate(
                '(el) => getComputedStyle(el.parentElement).getPropertyValue("--reporttkt-toc-indent")'
            ).strip()
            == f'{min(index, 2) * 0.75:g}rem'
        )
        assert float(
            link.evaluate('(el) => getComputedStyle(el).fontSize').removesuffix('px')
        ) == pytest.approx(
            float(
                links.first.evaluate(
                    '(el) => getComputedStyle(el).fontSize'
                ).removesuffix('px')
            )
            * (1 if index == 0 else 0.95)
        )
        assert link.evaluate('(el) => getComputedStyle(el).paddingTop') == '5.6px'
    for button in page.locator('.report-toc-toggle').all():
        box = button.bounding_box()
        assert box['width'] == box['height'] == 28
    for dark in (False, True):
        if dark:
            page.locator('.report-theme-toggle').click()

        # Resolve tokens in a probe so browser color serialization is identical.
        def token_color(link, token):
            return link.evaluate(
                """(el, token) => {
                const probe = document.createElement('span');
                probe.style.color = `var(${token})`;
                el.append(probe);
                const color = getComputedStyle(probe).color;
                probe.remove();
                return color;
            }""",
                token,
            )

        inactive = links.nth(len(levels))
        assert inactive.evaluate('(el) => getComputedStyle(el).color') == token_color(
            inactive, '--reporttkt-muted'
        )
        assert links.first.evaluate(
            '(el) => getComputedStyle(el).color'
        ) == token_color(links.first, '--reporttkt-text')
        current = links.nth(len(levels) - 1)
        assert current.evaluate('(el) => getComputedStyle(el).color') == token_color(
            current, '--reporttkt-toc-accent'
        )
        inactive.hover()
        assert inactive.evaluate('(el) => getComputedStyle(el).color') == token_color(
            inactive, '--reporttkt-text'
        )
        page.mouse.move(0, 0)
        inactive.focus()
        page.keyboard.press('Tab')
        page.keyboard.press('Shift+Tab')
        assert inactive.evaluate('(el) => getComputedStyle(el).outlineStyle') == 'solid'
        inactive.blur()
    # An expanded branch outside the active path remains neutral.
    page.locator('[data-reporttkt-heading="1"]').nth(1).evaluate(
        '(el) => el.scrollIntoView()'
    )
    page.wait_for_timeout(100)
    assert links.first.evaluate('(el) => getComputedStyle(el).color') == token_color(
        links.first, '--reporttkt-muted'
    )
    assert links.first.evaluate('(el) => getComputedStyle(el).boxShadow') == 'none'
    for width in (1440, 500, 320):
        page.set_viewport_size({'width': width, 'height': 800})
        page.wait_for_timeout(100)
        if width == 500:
            page.locator('.report-reader-toggle').click()
        nav = page.locator('.report-toc')
        nav.evaluate('(el) => el.scrollTop = el.scrollHeight')
        assert page.locator('.report-reader-toc-header').bounding_box()[
            'y'
        ] == pytest.approx(nav.bounding_box()['y'], abs=1)
        assert nav.evaluate('(el) => el.scrollWidth <= el.clientWidth')
        assert page.locator('.report-sidebar').evaluate(
            '(el) => el.scrollHeight <= el.clientHeight'
        )
    page.close()


def test_reader_width_markup():
    profile = get_profile('rich').with_overrides(
        name='untitled', include_toc_title=False
    )
    for report in (reader_report(), Report()):
        html = report.to_html(toc=True, toc_position='reader', profile=profile)
        assert html.index('<button class="report-width-toggle"') < html.index(
            '<button class="report-theme-toggle"'
        )
        assert 'aria-label="Content width: Standard. Switch to Wide."' in html
        assert (
            'role="tooltip" hidden>Content width: Standard. Switch to Wide.</span>'
            in html
        )
        for mode in ('standard', 'wide'):
            assert f'data-reader-icon="width-{mode}"' in html
    assert 'data-reader-icon="width-narrow"' not in html
    for position in ('top', 'sidebar'):
        assert '<button class="report-width-toggle"' not in reader_report().to_html(
            toc=True, toc_position=position
        )


@pytest.mark.parametrize('standard_width', [1040, 900])
def test_reader_width_layout_state_and_restoration(browser, tmp_path, standard_width):
    from report_toolkit import Theme

    theme = Theme(name='width-test', tokens={'content_width': f'{standard_width}px'})
    html = reader_report().to_html(
        toc=True, toc_position='reader', collapsible_toc=True, style={'theme': theme}
    )
    page = browser.new_page(viewport={'width': 1800, 'height': 800})
    page.set_content(html)
    width = page.locator('.report-width-toggle')
    root = page.locator('.report-reader')
    article = page.locator('article')
    toggle = page.locator('.report-reader-toggle')
    heading = page.locator('#reporttkt-deep')
    heading.evaluate('(el) => el.scrollIntoView()')
    page.wait_for_timeout(100)
    page.locator('.report-reader-collapse').click()
    top = heading.bounding_box()['y']
    crumbs = page.locator('.report-breadcrumbs').inner_text()
    padding = article.evaluate('(el) => getComputedStyle(el).padding')
    bar_width = page.locator('.report-reader-bar-inner').bounding_box()['width']
    for sidebar_open in (True, False):
        if not sidebar_open:
            toggle.click()
            page.wait_for_timeout(100)
        for mode, factor, next_mode in (
            ('standard', 1, 'Wide'),
            ('wide', 1.25, 'Standard'),
        ):
            assert root.get_attribute('data-reader-width') == mode
            assert (
                width.get_attribute('aria-label')
                == f'Content width: {mode.title()}. Switch to {next_mode}.'
            )
            assert width.locator(f'[data-reader-icon="width-{mode}"]').is_visible()
            assert width.locator('svg:not([hidden])').count() == 1
            box = root.bounding_box()
            assert article.bounding_box()['width'] == pytest.approx(
                standard_width * factor, abs=1
            )
            assert box['width'] == pytest.approx(
                standard_width * factor + (280 if sidebar_open else 0), abs=1
            )
            assert box['x'] + box['width'] / 2 == pytest.approx(900, abs=1)
            assert article.evaluate('(el) => getComputedStyle(el).padding') == padding
            assert (
                page.locator('.report-reader-bar-inner').bounding_box()['width']
                == bar_width
            )
            assert heading.bounding_box()['y'] == pytest.approx(top, abs=2)
            assert page.locator('.report-breadcrumbs').inner_text() == crumbs
            assert page.locator('.report-toc a[aria-current]').inner_text() == 'Deep'
            assert page.locator('.report-toc-toggle[aria-expanded="true"]').count() == 0
            assert page.evaluate('location.hash') == ''
            width.click()
            page.wait_for_timeout(100)
            assert width.evaluate('(el) => el === document.activeElement')
    # Multiple activations before restoration completes retain the original anchor.
    width.evaluate('(el) => { el.click(); el.click(); }')
    page.wait_for_timeout(100)
    assert root.get_attribute('data-reader-width') == 'standard'
    assert heading.bounding_box()['y'] == pytest.approx(top, abs=2)
    width.evaluate("""el => {
        el.click();
        document.querySelector('.report-reader-toggle').click();
    }""")
    page.set_viewport_size({'width': 1600, 'height': 800})
    page.wait_for_timeout(150)
    assert root.get_attribute('data-reader-width') == 'wide'
    assert heading.bounding_box()['y'] == pytest.approx(top, abs=2)
    page.locator('.report-theme-toggle').click()
    assert root.get_attribute('data-reader-width') == 'wide'
    width.click()
    assert root.get_attribute('data-reader-theme') == 'dark'
    page.wait_for_timeout(100)
    for viewport in (1100, 500, 320):
        page.set_viewport_size({'width': viewport, 'height': 800})
        page.wait_for_timeout(100)
        for _ in range(2):
            width.click()
            page.wait_for_timeout(100)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            box = article.bounding_box()
            if viewport < 1100:
                assert box['x'] + box['width'] / 2 == pytest.approx(viewport / 2, abs=1)
            for control in (width, page.locator('.report-theme-toggle'), toggle):
                control_box = control.bounding_box()
                assert control_box['width'] == 40
                assert 0 <= control_box['x'] <= viewport - 40
        if viewport == 500:
            toggle.click()
            assert root.get_attribute('data-reader-width') == 'standard'
            assert article.bounding_box()['width'] <= viewport
            page.locator('.report-reader-close').click()
    page.set_viewport_size({'width': 1800, 'height': 800})
    page.wait_for_timeout(100)
    width.click()
    page.wait_for_timeout(100)
    wide_width = article.bounding_box()['width']
    page.emulate_media(media='print')
    assert not width.is_visible()
    assert article.bounding_box()['width'] == pytest.approx(standard_width, abs=1)
    page.emulate_media(media='screen')
    assert root.get_attribute('data-reader-width') == 'wide'
    assert article.bounding_box()['width'] == pytest.approx(wide_width, abs=1)
    path = tmp_path / 'width.html'
    path.write_text(html)
    page.goto(path.as_uri())
    width.click()
    page.reload()
    assert root.get_attribute('data-reader-width') == 'standard'
    page.close()


def test_reader_width_keyboard_tooltips_and_fallback(browser):
    html = Report().to_html(toc=True, toc_position='reader')
    page = browser.new_page(viewport={'width': 1800, 'height': 800})
    page.set_content(html)
    width = page.locator('.report-width-toggle')
    page.wait_for_timeout(100)
    width.focus()
    page.keyboard.press('Tab')
    page.keyboard.press('Shift+Tab')
    assert width.evaluate('(el) => getComputedStyle(el).outlineStyle') == 'solid'
    assert width.locator('[role="tooltip"]').is_visible()
    page.keyboard.press('Escape')
    assert not width.locator('[role="tooltip"]').is_visible()
    for key, mode in (
        ('Enter', 'wide'),
        (' ', 'standard'),
        ('Enter', 'wide'),
        (' ', 'standard'),
    ):
        page.keyboard.press(key)
        assert page.locator('.report-reader').get_attribute('data-reader-width') == mode
        assert width.evaluate('(el) => el === document.activeElement')
    page.mouse.move(0, 200)
    width.hover()
    assert width.locator('[role="tooltip"]').is_visible()
    assert (
        width.locator('[role="tooltip"]').inner_text()
        == 'Content width: Standard. Switch to Wide.'
    )
    page.close()
    page = browser.new_page(
        java_script_enabled=False, viewport={'width': 1800, 'height': 800}
    )
    page.set_content(html)
    assert not page.locator('.report-width-toggle').is_visible()
    assert page.locator('article').bounding_box()['width'] == 1040
    page.close()


@pytest.mark.parametrize('position', ['top', 'sidebar', 'reader'])
def test_toc_branches_are_opt_in(position, tmp_path):
    report = reader_report()
    options = {'toc': True, 'toc_position': position}
    html = report.to_html(**options)
    assert html == report.to_html(**options, collapsible_toc=False)
    assert html == HTMLWriter(**options).render(report.document)
    assert html == report.write(tmp_path / 'report.html', **options).read_text()
    assert 'data-reporttkt-navigation="false"' in html
    assert '<button class="report-toc-toggle"' not in html
    assert '<button class="report-reader-collapse"' not in html
    assert '<button class="report-toc-toggle"' in report.to_html(
        **options, collapsible_toc=True
    )

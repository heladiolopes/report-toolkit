import base64
import re
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from report_toolkit import (
    AdapterRegistry,
    HTMLWriter,
    RenderedArtifact,
    RenderingProfile,
    Report,
    get_profile,
)
from report_toolkit.adapters import AltairAdapter, PlotlyAdapter


def sample_report():
    report = Report('Review', description='Summary', author='Analyst')
    report.heading(1, 'Results')
    report.markdown('Some **results**.')
    with report.columns(2):
        with report.panel('First'):
            report.raw_html(
                '<table id="data" class="existing"><tr><th>A</th><td>1</td></tr></table>'
            )
        report.unordered(['Second'])
    return report


def test_builtin_profiles_and_export_paths(tmp_path):
    report = sample_report()
    original = report.document.children
    assert report.to_html() == report.to_html(profile='rich')
    assert report.to_html(fragment=True) == report.to_html(
        profile=get_profile('rich'), fragment=True
    )
    portable = report.to_html(profile='portable', toc=True, numbered_headings=True)
    assert portable.startswith('<!doctype html>')
    assert '<script' not in portable
    content = report.to_html(profile='content', toc=True, numbered_headings=True)
    assert content == report.to_html(
        profile='content', fragment=True, toc=True, numbered_headings=True
    )
    assert '<!doctype' not in content and '<head>' not in content
    assert '--reporttkt-font-family:' not in content
    assert 'grid-template-columns' in content
    assert '.reporttkt:where([data-reporttkt-layout])' in content
    assert 'data-reporttkt-layout="minimal"' in content
    assert 'report-panel-title' in content and '>First<' in content
    assert 'href="#reporttkt-results"' in content
    assert 'href="#reporttkt_toc"' in content
    assert '>1. Results' in content
    assert report.document.children == original
    path = report.write(tmp_path / 'content.html', profile='content', pretty=True)
    assert path.read_text() == report.to_html(profile='content', pretty=True)
    assert '--reporttkt-font-family:' not in report.to_html(
        profile='content', style={'mode': 'dark'}
    )


def test_class_mapping_preserves_payloads_and_existing_attributes():
    profile = get_profile('content').with_overrides(
        name='host',
        element_classes={
            'table': ('host-table', 'existing'),
            'td': ('host-cell',),
            'p': ('host-paragraph',),
            'img': ('host-image',),
        },
    )
    report = sample_report()
    script = '<script>const html = "<table class=original>";\nconst x = 1 < 2 && 3 > 2;</script>'
    style = '<style>.x::after { content: "<table>"; }</style>'
    raw = """<TABLE data-info='class="fake"' CLASS='existing\nother' style="color:red"><td class=cell>Text &amp; more</td></TABLE><img src="x"/>"""
    report.raw_html(script + style + raw)
    html = report.to_html(profile=profile)
    assert script in html and style in html
    assert 'class="existing host-table"' in html
    assert 'class="existing other host-table"' in html
    assert 'class="cell host-cell"' in html
    assert 'data-info=\'class="fake"\'' in html
    assert 'style="color:red"' in html and 'Text &amp; more' in html
    assert '<img src="x" class="host-image"/>' in html
    assert '<p class="host-paragraph">Some' in html


def test_profile_overrides_freeze_and_clear_classes():
    classes = {'td': ('host-cell',)}
    profile = RenderingProfile(name='host', element_classes=classes)
    classes['td'] = ('changed',)
    assert profile.element_classes['td'] == ('host-cell',)
    with pytest.raises(TypeError):
        profile.element_classes['td'] = ('changed',)
    derived = profile.with_overrides(
        name='derived', element_classes={'td': (), 'th': ('host-header',)}
    )
    assert derived.element_classes == {'td': (), 'th': ('host-header',)}
    assert profile.element_classes == {'td': ('host-cell',)}


@pytest.mark.parametrize(
    'kwargs, error',
    [
        ({'name': ''}, ValueError),
        ({'chart_mode': 'png'}, ValueError),
        ({'chart_mode': 'svg'}, ValueError),
        ({'content_only': 1}, TypeError),
        ({'include_metadata': 1}, TypeError),
        ({'include_toc_title': 'yes'}, TypeError),
        ({'stylesheet': 'unknown'}, ValueError),
        ({'toc_positions': ()}, ValueError),
        ({'element_classes': {'TD': ('x',)}}, ValueError),
        ({'element_classes': {'td': 'x'}}, TypeError),
        ({'element_classes': {'td': ('two classes',)}}, ValueError),
    ],
)
def test_invalid_profiles(kwargs, error):
    with pytest.raises(error):
        RenderingProfile(**({'name': 'custom'} | kwargs))


@pytest.mark.parametrize('profile', ['rich', 'portable', 'content'])
def test_profile_metadata_and_toc_title(profile, tmp_path):
    report = Report(
        'Report title',
        description='Report description',
        author='Report author',
        date='2026-09-30',
    )
    report.heading(1, 'Results')
    report.paragraph('Composed content')
    metadata = ('Report title', 'Report description', 'Report author', '2026-09-30')
    html = report.to_html(profile=profile, toc=True)
    for value in metadata:
        assert (value in html) == (profile != 'content')
    assert ('<div class="report-toc-title">' in html) == (profile != 'content')
    assert 'aria-label="Table of contents"' in html
    assert 'href="#reporttkt-results"' in html
    assert 'href="#reporttkt_toc"' in html
    assert 'Composed content' in html
    assert metadata == (
        report.document.title,
        report.document.description,
        report.document.author,
        report.document.date,
    )
    path = report.write(tmp_path / 'report.html', profile=profile, toc=True)
    assert path.read_text() == html


@pytest.mark.parametrize('field', ['include_metadata', 'include_toc_title'])
def test_content_profile_can_restore_metadata_and_toc_title_independently(field):
    profile = get_profile('content').with_overrides(name='custom', **{field: True})
    report = sample_report()
    html = HTMLWriter(profile=profile, toc=True).render(report.document)
    assert ('<h1 class="report-title">Review</h1>' in html) == (
        field == 'include_metadata'
    )
    assert ('<div class="report-toc-title">' in html) == (field == 'include_toc_title')
    assert not get_profile('content').include_metadata
    assert not get_profile('content').include_toc_title


def test_full_page_profile_can_omit_metadata():
    profile = get_profile('rich').with_overrides(
        name='anonymous', include_metadata=False
    )
    html = sample_report().to_html(profile=profile)
    assert '<title>Report</title>' in html
    assert 'Review' not in html and 'Summary' not in html and 'Analyst' not in html


def test_writer_profile_validation():
    with pytest.raises(ValueError, match='Unknown profile'):
        HTMLWriter(profile='unknown')
    with pytest.raises(TypeError):
        HTMLWriter(profile=None)
    with pytest.raises(ValueError, match='TOC'):
        HTMLWriter(profile='content', toc=False, toc_position='sidebar')
    with pytest.raises(ValueError, match='inline_altair'):
        HTMLWriter(profile='portable', inline_altair=True)
    with pytest.raises(ValueError):
        Report().to_html(profile='content', style={'mode': 'invalid'})


def test_legacy_and_profile_aware_adapters():
    class Legacy:
        def render(self, value):
            return RenderedArtifact('<table><td>legacy</td></table>')

    class Aware:
        def render_for_profile(self, value, *, profile):
            return RenderedArtifact(f'<p>{profile.chart_mode}</p>')

    report = Report()
    report.add(object())
    registry = AdapterRegistry()
    registry.register(object, Legacy())
    assert 'legacy' in HTMLWriter(registry=registry, profile='content').render(
        report.document
    )
    with pytest.raises(TypeError, match='render_for_profile'):
        HTMLWriter(registry=registry, profile='portable').render(report.document)
    registry.register(object, Aware())
    assert '<p>svg</p>' in HTMLWriter(registry=registry, profile='portable').render(
        report.document
    )


def test_exporter_dependency_errors_and_failure():
    value = SimpleNamespace(layout=SimpleNamespace(width=400))
    with (
        patch.dict(sys.modules, {'vl_convert': None}),
        pytest.raises(ImportError, match=r'report-toolkit\[portable\]'),
    ):
        AltairAdapter().render_for_profile(value, profile=get_profile('portable'))
    pytest.importorskip('plotly')
    with (
        patch.dict(sys.modules, {'kaleido': None}),
        pytest.raises(ImportError, match=r'report-toolkit\[portable\]'),
    ):
        PlotlyAdapter().render_for_profile(value, profile=get_profile('portable'))
    with (
        patch.dict(sys.modules, {'kaleido': SimpleNamespace()}),
        patch('plotly.io.to_image', side_effect=RuntimeError('export failed')),
    ):
        with pytest.raises(RuntimeError, match='Chrome') as error:
            PlotlyAdapter().render_for_profile(value, profile=get_profile('portable'))
        assert str(error.value.__cause__) == 'export failed'


def test_plotly_svg_adapter_contract():
    pytest.importorskip('plotly')
    value = SimpleNamespace(layout=SimpleNamespace(width=400))
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><text>Chart</text></svg>'
    with (
        patch.dict(sys.modules, {'kaleido': SimpleNamespace()}),
        patch('plotly.io.to_image', return_value=svg) as export,
    ):
        result = PlotlyAdapter().render_for_profile(
            value, profile=get_profile('portable')
        )
    export.assert_called_once_with(value, format='svg')
    assert base64.b64encode(svg).decode() in result.html
    assert result.native_width == 400


def test_altair_svg_and_content_integration():
    alt = pytest.importorskip('altair')
    pytest.importorskip('vl_convert')
    report = Report()
    chart = (
        alt.Chart(alt.Data(values=[{'x': 1, 'y': 2}]))
        .mark_point()
        .encode(x='x:Q', y='y:Q')
    )
    report.add(chart, caption='Trend', width='full', center=False)
    report.add(chart)
    html = report.to_html(profile='portable')
    images = re.findall(r'data:image/svg\+xml;base64,([^" ]+)', html)
    assert len(images) == 2
    assert all('<svg' in base64.b64decode(image).decode() for image in images)
    assert '<script' not in html
    assert '<figcaption>Trend</figcaption>' in html
    assert 'data-width="full" data-center="false"' in html
    content = report.to_html(profile='content')
    assert content.count('vegaEmbed(') == 2
    assert 'report-artifact-dialog' not in content


def test_pandas_classes_and_formatting():
    pd = pytest.importorskip('pandas')
    report = Report()
    report.add(
        pd.DataFrame({'value': [12]})
        .style.format('${:.2f}')
        .set_properties(color='red')
    )
    profile = get_profile('content').with_overrides(
        name='host',
        element_classes={
            'table': ('host-table',),
            'th': ('host-header',),
            'td': ('host-cell',),
        },
    )
    html = report.to_html(profile=profile)
    assert 'host-table' in html and 'host-header' in html and 'host-cell' in html
    assert '$12.00' in html and 'color: red' in html
    assert 'row0 col0 host-cell' in html
    assert '<script' not in report.to_html(profile='portable')


def test_templates_use_profiles_without_recomposition():
    report = Report.from_template_string('# Results\n\nSome **results**.')
    assert '>Results<' in report.to_html(profile='content', toc=True)
    assert report.to_html(profile='portable').startswith('<!doctype html>')


def test_plotly_content_keeps_interactive_html():
    go = pytest.importorskip('plotly.graph_objects')
    report = Report()
    report.add(go.Figure(data=go.Bar(x=['Jan'], y=[12])), caption='Revenue')
    html = report.to_html(profile='content')
    assert 'Plotly.newPlot(' in html and 'cdn.plot.ly' in html
    assert '<!doctype' not in html and 'report-artifact-dialog' not in html


def test_plotly_svg_integration():
    go = pytest.importorskip('plotly.graph_objects')
    pytest.importorskip('kaleido')
    chromium = pytest.importorskip('choreographer.browsers.chromium')
    chart = go.Figure(data=go.Bar(x=['Jan'], y=[12]))
    report = Report()
    report.add(chart, caption='Revenue')
    try:
        html = report.to_html(profile='portable')
    except RuntimeError as error:
        cause = error.__cause__
        if isinstance(cause, chromium.ChromeNotFoundError) or 'Chrome' in str(cause):
            pytest.skip('Chrome is not installed for Kaleido')
        raise
    image = re.search(r'data:image/svg\+xml;base64,([^" ]+)', html)[1]
    assert '<svg' in base64.b64decode(image).decode()
    assert '<script' not in html and '<figcaption>Revenue</figcaption>' in html


def test_matplotlib_remains_png_in_portable():
    Figure = pytest.importorskip('matplotlib.figure').Figure
    figure = Figure(figsize=(2, 1))
    figure.subplots().plot([1, 2], [3, 4])
    report = Report()
    report.add(figure)
    html = report.to_html(profile='portable')
    assert 'data:image/png;base64,' in html and '<script' not in html


def test_classes_apply_to_full_document_structure():
    profile = get_profile('rich').with_overrides(
        name='host-page',
        element_classes={'body': ('host-body',), 'article': ('host-report',)},
    )
    html = Report('Review').to_html(profile=profile)
    assert '<body class="host-body">' in html
    assert 'class="reporttkt host-report"' in html

"""Scalar filters through the public template API."""

from datetime import date
from decimal import Decimal
from html import escape

import pytest

from report_toolkit import Report, TemplateError


@pytest.mark.parametrize(
    ('filters', 'expected'),
    [
        ('quote', '&quot;hello&quot;'),
        ('strong', '<strong>hello</strong>'),
        ('em', '<em>hello</em>'),
        ('code', '<code>hello</code>'),
        ('quote | strong', '<strong>&quot;hello&quot;</strong>'),
        ('strong | code', '<code>**hello**</code>'),
        ('code | strong', '<strong><code>hello</code></strong>'),
    ],
)
def test_filters_and_order(filters, expected):
    report = Report.from_template_string(
        '{{value|' + filters + '}}', context={'value': 'hello'}
    )
    assert expected in report.to_html(profile='content')


@pytest.mark.parametrize('filter_name', ['quote', 'strong', 'em', 'code'])
def test_filters_preserve_literal_values_and_contexts(filter_name):
    source = (
        'Prose {{ value | FILTER }}.\n\n'
        '- {{ value | FILTER }}\n\n'
        '> {{ value | FILTER }}\n\n'
        '[{{ value | FILTER }}](https://example.org)\n\n'
        '| Value |\n| --- |\n| {{ value | FILTER }} |\n'
    ).replace('FILTER', filter_name)
    report = Report.from_template_string(
        source, context={'value': '*hello* <b> & {{ absent }}'}
    )
    html = report.to_html(profile='content')
    assert html.count('*hello* &lt;b&gt; &amp; {{ absent }}') == 5
    assert '<em>hello</em>' not in html
    assert '<b>' not in html
    assert '<td>' in html


@pytest.mark.parametrize('value', [42, Decimal('1.25'), True, date(2026, 10, 22), ''])
def test_filters_convert_scalars(value):
    report = Report.from_template_string(
        '{{ value | quote | strong }}', context={'value': value}
    )
    assert f'<strong>&quot;{value}&quot;</strong>' in report.to_html(profile='content')


@pytest.mark.parametrize('filter_name', ['strong', 'em', 'code'])
def test_empty_styling_filters(filter_name):
    report = Report.from_template_string(
        'Before {{ value | ' + filter_name + ' }} after.', context={'value': ''}
    )
    assert '<p>Before  after.</p>' in report.to_html(profile='content')


@pytest.mark.parametrize('value', ['`hello``', '`', 'a \\ b', r'A\|B', '  a\n b  '])
def test_code_preserves_backticks_backslashes_and_normalizes_whitespace(value):
    report = Report.from_template_string('{{ value | code }}', context={'value': value})
    assert '<code>' + ' '.join(value.split()) + '</code>' in report.to_html(
        profile='content'
    )


def test_plain_labels_keep_quotes_without_styling():
    report = Report.from_template_string(
        '# {{ value | strong | code | quote }}\n\n'
        '{% panel "{{ value | quote | em }}" %}\nText\n{% endpanel %}',
        context={'value': '*hello*'},
    )
    section = report.document.children[0]
    assert section.title == '"*hello*"'
    assert section.children[0].title == '"*hello*"'
    html = report.to_html(profile='content')
    assert '<strong>' not in html and '<em>' not in html and '<code>' not in html


def test_caption_filters_are_plain_text():
    from test_templates import _Adapter, _Chart

    from report_toolkit import AdapterRegistry, HTMLWriter

    report = Report.from_template_string(
        '{% artifact chart caption="{{ value | strong | quote }}" %}',
        context={'chart': _Chart(), 'value': '*hello*'},
    )
    registry = AdapterRegistry()
    registry.register(_Chart, _Adapter())
    html = HTMLWriter(registry=registry).render(report.document)
    assert '&quot;*hello*&quot;' in html
    assert '<strong>' not in html


@pytest.mark.parametrize(
    ('expression', 'value', 'message'),
    [
        ('value | unknown', 'hello', 'Unknown template filter: unknown'),
        ('value |', 'hello', 'simple context key'),
        ('value || strong', 'hello', 'simple context key'),
        ('value | quote("x")', 'hello', 'simple context key'),
        ('value.other | strong', 'hello', 'simple context key'),
        ('value | strong', object(), 'require a scalar'),
        ('value | strong', None, 'cannot be None'),
    ],
)
def test_filter_errors_have_locations(tmp_path, expression, value, message):
    path = tmp_path / 'report.md'
    path.write_text('\n{{ ' + expression + ' }}', encoding='utf-8')
    with pytest.raises(TemplateError, match=message) as error:
        Report.from_template(path, context={'value': value})
    assert f'{path}:2:' in str(error.value)


def test_filtered_placeholders_stay_literal_in_excluded_contexts():
    report = Report.from_template_string(
        '`{{ absent | unknown }}`\n\n'
        '```\n{{ absent | unknown }}\n```\n\n'
        '    {{ absent | unknown }}\n\n'
        '\\{{ absent | unknown }}\n\n'
        '<div>{{ absent | unknown }}</div>\n\n'
        'Text <span>{{ absent | unknown }}</span>.'
    )
    assert report.to_html(profile='content').count('{{ absent | unknown }}') == 6


def test_filtered_link_destinations_remain_unsupported():
    with pytest.raises(TemplateError, match='destinations'):
        Report.from_template_string(
            '[link]({{ url | quote }})', context={'url': 'https://example.org'}
        )


@pytest.mark.parametrize(
    'value', ['A|B', 'A\\|B', 'A\\\\|B', '`A|B`', 'A|<b> & {{ absent }}']
)
@pytest.mark.parametrize('filters', ['code', 'code | strong', 'strong | code'])
def test_code_pipes_stay_in_one_table_cell(value, filters):
    report = Report.from_template_string(
        '| Value |\n| --- |\n| {{ value | ' + filters + ' }} |\n',
        context={'value': value},
    )
    html = report.to_html(profile='content')
    assert html.count('<td>') == 1
    expected = escape(value, quote=False)
    if filters == 'strong | code':
        expected = '**' + expected + '**'
    assert '<code>' + expected + '</code>' in html

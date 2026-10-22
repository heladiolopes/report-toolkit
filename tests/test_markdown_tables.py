import pytest

from report_toolkit import Report


@pytest.mark.parametrize('profile', ['rich', 'portable', 'content'])
@pytest.mark.parametrize('template', [False, True])
def test_pipe_tables_render_with_alignment_and_inline_content(profile, template):
    source = (
        '| Metric | Detail | Value |\n'
        '| :--- | :---: | ---: |\n'
        '| **Revenue** | A\\|B and `code` | 12 |\n'
        '| <script>unsafe</script> | Text | 7 |\n'
    )
    if template:
        report = Report.from_template_string(source)
    else:
        report = Report()
        report.markdown(source)

    html = report.to_html(profile=profile)
    assert '<table>' in html
    assert '<thead>' in html and '<tbody>' in html
    assert '<th style="text-align:right">Value</th>' in html
    assert '<td style="text-align:left"><strong>Revenue</strong></td>' in html
    assert '<td style="text-align:center">A|B and <code>code</code></td>' in html
    assert '<td style="text-align:right">12</td>' in html
    assert '&lt;script&gt;unsafe&lt;/script&gt;' in html
    assert '<script>unsafe</script>' not in html


def test_template_table_values_cannot_introduce_cells_or_markup():
    report = Report.from_template_string(
        '# Results\n\n{% panel "Summary" %}\n'
        '| Metric | Value |\n| --- | --- |\n'
        '| {{ label }} | {{ value }} |\n{% endpanel %}\n',
        context={'label': 'A|B', 'value': '**12** <script>unsafe</script>'},
    )
    html = report.to_html(profile='content')
    assert '<td>A|B</td>' in html
    assert '<td>**12** &lt;script&gt;unsafe&lt;/script&gt;</td>' in html
    assert html.count('<td>') == 2


@pytest.mark.parametrize('template', [False, True])
def test_fenced_pipe_table_remains_code(template):
    source = '```markdown\n| Metric | Value |\n| --- | --- |\n| Revenue | 12 |\n```\n'
    if template:
        report = Report.from_template_string(source)
    else:
        report = Report()
        report.markdown(source)
    html = report.to_html(profile='content')
    assert '<table>' not in html
    assert '<pre><code class="language-markdown">| Metric | Value |' in html

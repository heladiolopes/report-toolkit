import builtins
import subprocess
import sys
from datetime import date
from unittest.mock import patch

import pytest

from report_toolkit import Node, NotebookWriter, Report


def test_notebook_dependencies_are_lazy_and_missing_dependencies_are_actionable():
    # A fresh interpreter also catches accidental optional imports at package load.
    subprocess.run(
        [
            sys.executable,
            '-c',
            (
                'import sys; import report_toolkit; '
                'assert "IPython" not in sys.modules; '
                'assert "ipywidgets" not in sys.modules; '
                'assert "<!doctype html>" in report_toolkit.Report().to_html()'
            ),
        ],
        check=True,
    )
    original_import = builtins.__import__

    for missing in ('IPython', 'ipywidgets'):

        def blocked_import(name, *args, missing=missing, **kwargs):
            if name.split('.')[0] == missing:
                raise ImportError('dependency unavailable')
            return original_import(name, *args, **kwargs)

        with (
            patch('builtins.__import__', side_effect=blocked_import),
            pytest.raises(ImportError, match=r'report-toolkit\[notebook\]'),
        ):
            Report().display()


def notebook_modules():
    ipdisplay = pytest.importorskip('IPython.display')
    widgets = pytest.importorskip('ipywidgets')
    return ipdisplay, widgets


def test_markdown_tables_in_notebook_display():
    ipdisplay, _ = notebook_modules()
    report = Report.from_template_string(
        '| Metric | Value |\n| --- | ---: |\n| **Revenue** | 12 |\n'
    )
    with patch.object(ipdisplay, 'display') as display:
        report.display()
    html = display.call_args.args[0].data
    assert '<table>' in html
    assert '<td><strong>Revenue</strong></td>' in html
    assert '<td style="text-align:right">12</td>' in html


def test_native_artifacts_and_plain_text_structure():
    ipdisplay, _ = notebook_modules()
    artifact = object()  # Native display accepts objects without an HTML adapter.
    report = Report(
        'Title <one>',
        description='Summary & details',
        author='A',
        date=date(2026, 1, 2),
    )
    report.heading(3, 'Section <three>')
    report.markdown('**Bold** <script>unsafe</script>')
    report.raw_html('<hr>')
    report.ordered(['Parent & child', ['Nested', ['Deep']], 'Last'])
    with report.panel('Panel <label>'):
        report.add(
            artifact,
            caption='Hidden caption',
            width='full',
            center=False,
            expand='always',
        )
    with patch.object(ipdisplay, 'display') as display:
        assert report.display() is None
    values = [call.args[0] for call in display.call_args_list]
    assert values[-1] is artifact
    text = [value.data for value in values[:-1]]
    assert text[:5] == [
        '<h1>Title &lt;one&gt;</h1>',
        '<p>Summary &amp; details</p>',
        '<p>A</p>',
        '<p>2026-01-02</p>',
        '<h3>Section &lt;three&gt;</h3>',
    ]
    assert '<strong>Bold</strong>' in text[5]
    assert '&lt;script&gt;' in text[5]
    assert text[6] == '<hr>'
    assert text[7] == (
        '<ol><li>Parent &amp; child<ol><li>Nested<ol><li>Deep</li></ol>'
        '</li></ol></li><li>Last</li></ol>'
    )
    assert text[8] == '<p>Panel &lt;label&gt;</p>'
    assert 'Hidden caption' not in ''.join(text)


def test_columns_wrap_and_preserve_grouping_and_nested_native_display():
    ipdisplay, widgets = notebook_modules()
    report = Report()
    first, second = object(), object()
    with report.columns(2):
        with report.panel('Group'):
            report.add(first)
            report.markdown('Same cell')
        report.add(second)
        with report.columns(1):
            report.markdown('Nested cell')
    events = []
    active = []

    def enter(output):
        active.append(output)
        return output

    def leave(output, *args):
        assert active.pop() is output

    def record(value):
        events.append((value, active[-1] if active else None))

    with (
        patch.object(widgets.Output, '__enter__', enter),
        patch.object(widgets.Output, '__exit__', leave),
        patch.object(ipdisplay, 'display', side_effect=record),
    ):
        NotebookWriter().display(report.document)

    grid, target = events[0]
    assert isinstance(grid, widgets.GridBox)
    assert target is None
    assert len(grid.children) == 3
    assert grid.layout.grid_template_columns == 'repeat(2, minmax(0, 1fr))'
    assert all(isinstance(child, widgets.Output) for child in grid.children)
    assert [target for _, target in events[1:4]] == [grid.children[0]] * 3
    assert events[2][0] is first
    assert events[4] == (second, grid.children[1])
    nested, target = events[5]
    assert isinstance(nested, widgets.GridBox)
    assert target is grid.children[2]
    assert nested.layout.grid_template_columns == 'repeat(1, minmax(0, 1fr))'
    assert events[6][1] is nested.children[0]


def test_empty_report_and_columns_and_errors_inside_output():
    ipdisplay, _ = notebook_modules()
    report = Report()
    with patch.object(ipdisplay, 'display') as display:
        report.display()
        display.assert_not_called()
        with report.columns(3):
            pass
        report.display()
        assert display.call_args.args[0].children == ()

    broken = Report()
    with broken.columns(1) as columns:
        columns.append(Node())
    with (
        patch.object(ipdisplay, 'display'),
        pytest.raises(TypeError, match='Cannot display node type Node'),
    ):
        broken.display()

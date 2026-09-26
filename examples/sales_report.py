"""Run with `python examples/sales_report.py` after installing reportkit[all]."""

from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import plotly.graph_objects as go
from matplotlib.figure import Figure

from reportkit import HTMLWriter, Report


def main() -> None:
    sales = pd.DataFrame(
        {
            'month': ['Jan', 'Feb', 'Mar', 'Apr'],
            'revenue': [120, 145, 138, 167],
        }
    )
    chart = (
        alt.Chart(sales).mark_bar(color='#2563a6').encode(x='month:N', y='revenue:Q')
    )
    figure = Figure(figsize=(5, 3))
    axes = figure.subplots()
    axes.plot(sales['month'], sales['revenue'], marker='o', color='#2563a6')
    axes.set_ylabel('Revenue')
    plot = go.Figure(data=go.Bar(x=sales['month'], y=sales['revenue']))

    report = Report(
        'Sales analysis',
        description='Monthly revenue for the first four months',
        author='Analytics team',
        date=date.today(),
    )

    with report.section(title='Summary'):
        report.markdown('Revenue **increased** over the period, with a dip in March.')
        report.unordered(
            ['Highest month: April', 'Lowest month: January', ['Revenue: 120']]
        )
        report.add(
            sales.style.format({'revenue': '${:.2f}'}), caption='Monthly revenue'
        )

    with report.section('Trends'):
        with report.columns(2):
            with report.panel('Interactive trend'):
                report.add(chart, caption='Interactive view')
            with report.panel('Static trend'):
                report.add(figure, caption='Static view')
        report.add(plot, caption='Plotly view')

    output = Path('examples/sales_report.html')
    print(report.to_tree())
    HTMLWriter(toc=True, toc_depth=2).write(report.document, output)
    print(output.resolve())


if __name__ == '__main__':
    main()

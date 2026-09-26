"""Run with: uv run --extra all python examples/template_report.py."""

from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure

from reportkit import Report

sales = pd.DataFrame({'month': ['January', 'February'], 'revenue': [120, 145]})
figure = Figure(figsize=(5, 3))
figure.subplots().bar(sales['month'], sales['revenue'])
latest = sales['revenue'].iloc[-1]
growth = latest / sales['revenue'].iloc[-2] - 1

report = Report.from_template(
    Path(__file__).with_name('monthly_sales.md'),
    context={
        'period': 'February',
        'growth': f'{growth:.1%}',
        'latest_revenue': f'${latest:,.2f}',
        'revenue_table': sales.style.format({'revenue': '${:.2f}'}),
        'revenue_chart': figure,
    },
)
print(report.to_tree())
output = report.write(Path(__file__).with_name('template_report.html'), toc=True)
print(f'Wrote {output}')

# Getting Started

Create a sales report with a table, a summary, and a two-column layout.
Run these commands from a report-toolkit checkout:

```bash
uv sync --extra pandas
```

Save the following as `first_report.py` in the checkout:

```python
from datetime import date

import pandas as pd

from report_toolkit import Report

sales = pd.DataFrame({'month': ['January', 'February'], 'revenue': [12000, 14500]})
report = Report(
    'Sales review',
    description='Monthly revenue',
    author='Report author',
    date=date(2026, 3, 1),
)

report.heading(1, 'Summary')
report.markdown('Revenue rose from **$12,000** to **$14,500**.')

with report.section('Details'):
    with report.columns(2):
        with report.panel('Monthly results'):
            report.add(
                sales.style.hide(axis='index').format({'revenue': '${:,.0f}'}),
                caption='Revenue by month',
            )
        with report.panel('Next steps'):
            report.unordered(['Review the increase', 'Prepare the March forecast'])

output = report.write('first_report.html', toc=True)
print(output.resolve())
```

Run it and open the printed file path in your browser:

```bash
uv run --extra pandas python first_report.py
```

The report title and metadata appear above the table of contents. `heading()`
starts a section; subsequent content belongs to it until an equal or shallower
heading begins. The `section()` context creates a subsection and restores the
previous position when it ends. Here, “Details” sits inside “Summary”.

Each direct child of `columns()` occupies one grid cell. A `panel()` groups a
table, text, or several other elements into one cell. On narrow screens, the
columns stack vertically.

Objects passed to `add()` are rendered when you write the report, so finish
preparing your data before writing. This example embeds the table and needs no
network connection to view.

Continue with [Common Tasks](common-tasks.md) for charts and templates or the
[API Reference](api-reference.md) for exact method behavior. The
[paired sales examples](../README.md#two-equivalent-examples) show both authoring
methods producing a more complete report.

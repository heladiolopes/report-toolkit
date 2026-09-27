# Common Tasks

Examples assume `from reportkit import Report` and `report = Report('Analysis')`,
unless a complete setup is shown. Install the relevant extra from a checkout
with `uv sync --extra pandas`, for example, or use `--extra all` for every
integration below. For an existing environment, install the corresponding
`reportkit[pandas]` extra. See [Getting Started](getting-started.md) for a complete
runnable introduction and [API Reference](api-reference.md) for constraints.

## Add a Pandas table

```python
import pandas as pd

sales = pd.DataFrame({'month': ['Jan', 'Feb'], 'revenue': [12000, 14500]})
report.add(sales, caption='Source data')
report.add(
    sales.style.hide(axis='index').format({'revenue': '${:,.0f}'}),
    caption='Formatted revenue',
)
```

Requires the `pandas` extra. Both DataFrame and Styler are supported; Styler
preserves formatting and its own table caption. The report caption appears
beneath the artifact.

## Add an Altair chart

```python
import altair as alt
import pandas as pd

sales = pd.DataFrame({'month': ['Jan', 'Feb'], 'revenue': [12000, 14500]})
chart = alt.Chart(sales).mark_bar().encode(x='month:N', y='revenue:Q')
report.add(chart, caption='Monthly revenue')
```

Requires `altair` and, for this data setup, `pandas`. JavaScript loads from a CDN
by default. For embedded Altair JavaScript, install the `offline` extra and use:

```python
from reportkit import HTMLWriter

HTMLWriter(inline_altair=True).write(report.document, 'offline.html')
```

External data URLs still require access to those URLs. This option only changes
Altair output; it does not embed Plotly's dependencies.

## Add a Matplotlib figure

```python
from matplotlib.figure import Figure

figure = Figure(figsize=(5, 3), layout='constrained')
figure.subplots().bar(['Jan', 'Feb'], [12000, 14500])
report.add(figure, caption='Monthly revenue')
```

Requires `matplotlib`. The figure is embedded as a PNG; no GUI or separate image
file is needed.

## Add a Plotly chart

```python
import plotly.graph_objects as go

chart = go.Figure(data=go.Bar(x=['Jan', 'Feb'], y=[12000, 14500]))
report.add(chart, caption='Interactive revenue')
```

Requires `plotly`. Its JavaScript loads from a CDN. View interactive reports in a
browser with network access and permission to execute scripts; document hosts
may strip scripts or styles.

## Organize sections

```python
report.heading(1, 'Results')
report.paragraph('Overview of the results.')
with report.section('Revenue'):
    report.markdown('Revenue **increased**.')
report.heading(1, 'Next steps')
report.paragraph('Prepare the next review.')
```

Headings group subsequent content automatically. Larger levels create nested
sections; equal or smaller levels close the current heading group. Skipped
levels do not create extra sections. Context managers restore the previous
position and isolate heading grouping. Use `normalize=True` to convert a title
such as `monthly-sales` to `Monthly Sales`.

## Put content in columns and panels

```python
with report.columns(2):
    with report.panel('Results'):
        report.paragraph('Revenue increased.')
        report.unordered(['January: $12,000', 'February: $14,500'])
    with report.panel('Actions'):
        report.paragraph('Review the forecast.')
    with report.panel('Notes'):
        report.paragraph('This third item wraps onto the next row.')
```

Each direct child is one grid item. Panels group content together, show a label,
and scroll horizontally when needed. Panel labels do not appear in the TOC.
Panels also work outside columns, and layouts can nest.

## Add lists and Markdown

```python
report.unordered(['Results', ['Revenue increased', 'Costs were stable'], 'Actions'])
report.ordered(['Validate inputs', ['Check totals', 'Confirm dates'], 'Publish'])
report.markdown('Use **bold**, *italics*, `code`, and [links](https://example.com).')
report.markdown('> An observation.\n\n---\n\n```python\nprofit = revenue - cost\n```')
```

Nested Python lists follow a parent string and inherit the outer list style.
List strings are literal text. `paragraph()` uses the same Markdown rendering as
`markdown()`. HTML in Markdown is escaped. Use `heading()` for headings that
should participate in document structure and the TOC.

## Insert trusted HTML

```python
report.raw_html('<p>A <strong>trusted</strong> HTML fragment.</p>')
report.add('<p>Strings passed to add() are also trusted HTML.</p>')
```

Only insert HTML you trust; these methods do not escape it. Strings cannot have
artifact captions. Templates escape HTML and currently have no trusted HTML tag.
The paired examples therefore demonstrate shared display features only.

## Combine reports

```python
intro = Report('Combined report', author='Analytics')
intro.heading(1, 'Summary')
intro.paragraph('An overview.')
appendix = Report('Appendix')
appendix.heading(1, 'Details')
appendix.paragraph('Supporting observations.')
combined = intro + appendix  # equivalent to intro.concat(appendix)
combined.write('combined.html', toc=True)
```

The result keeps the left report's metadata. Content structure is copied;
analytical objects remain shared. Existing sections retain their boundaries.

## Build a report from a Markdown template

Save this as `monthly.md`:

```markdown
---
title: Monthly sales
author: Analytics
---

# Summary

Revenue increased by **{{ growth }}**.

{% columns 2 %}
{% panel "Revenue for {{ period }}" %}
{% artifact revenue_table caption="Revenue for {{ period }}" %}
{% endpanel %}
{% panel "Notes" %}
- Review the forecast.
{% endpanel %}
{% endcolumns %}
```

Load it from Python:

```python
import pandas as pd
from reportkit import Report

sales = pd.DataFrame({'month': ['Jan', 'Feb'], 'revenue': [12000, 14500]})
report = Report.from_template(
    'monthly.md',
    context={
        'growth': '20.8%',
        'period': 'February',
        'revenue_table': sales.style.format({'revenue': '${:,.0f}'}),
    },
)
report.write('monthly.html', toc=True)
```

This example requires `pandas` and `templates` (YAML metadata). Templates without
front matter need no template-specific dependency. For in-memory text:

```python
report = Report.from_template_string(
    '# Summary\n\nRevenue: {{ total }}.', context={'total': '$26,500'}
)
```

Prepare calculations, table styling, and display values in Python. Write
narrative and layout in the template. Scalars are inserted as literal text;
formatting belongs in the template. Analytical objects must appear on their own
line as `{{ chart }}` or an artifact tag. Templates do not evaluate Python or
support loops, conditionals, filters, indexing, attribute access, or includes.
See the [template reference](api-reference.md#template-syntax) for complete rules.

The [template example](../examples/template_report.py) and
[Python example](../examples/sales_report.py) produce equivalent sales reports.
Their shared helper contains only data and chart generation.

## Inspect and export a report

```python
print(report.to_tree())
html = report.to_html(toc=True, toc_depth=2)
path = report.write('report.html', toc=True, toc_depth=2)
fragment = report.to_html(fragment=True)
```

The tree shows structure without rendering artifacts. A fragment includes scoped
CSS and report content without the HTML document wrapper. The destination's
parent directory must already exist.

The TOC includes section headings up to the absolute depth selected. It excludes
the report title, panel labels, and headings inside Markdown or artifacts.

To show successful write paths and file sizes through Python logging:

```python
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
report.write('report.html')
```

The library logs through `reportkit.writer` and does not configure logging itself.


## Choose a report theme

```python
report.write('dark.html', theme='dark')
report.write('adaptive.html', theme='auto')
report.write('paper.html', theme='auto-paper')
```

Fixed presets are `light`, `dark`, `paper`, and `ink`. Automatic pairs follow the
reader's system preference. See [Themes](themes.md) to define a custom theme,
customize fonts and spacing, or pair your own light and dark styles.


### Number headings and move the TOC to a sidebar

```python
report.write(
    'report.html',
    toc=True,
    numbered_headings=True,
    toc_position='sidebar',
)
```

Heading numbers follow the report hierarchy and also appear in the TOC. Omit
`numbered_headings` to keep headings unnumbered. Use `toc_position='top'` (the
default) for a TOC below the report metadata with ↑ links from headings back to
the TOC.

Long sidebar TOCs scroll independently of the report on wide screens. On narrow
screens, the TOC moves above the content card and scrolls naturally with the page.
It stays fully visible without a toggle or JavaScript.

### Run browser navigation tests

Browser tests are optional and skip if Playwright or Chromium is unavailable.
Install and run them without adding a runtime dependency:

```sh
uv run --with playwright python -m playwright install chromium
uv run --with playwright pytest tests/test_navigation_options.py -q
```

These tests exercise long TOCs, desktop and mobile layouts,
print layout, and navigation in full documents and fragments.

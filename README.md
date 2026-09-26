# reportkit

Compose analytical reports in Python, then render them as styled HTML. A report stores its document structure until you ask a writer to render it.

## Install

```bash
python -m pip install -e '.[all]'
```

Install `reportkit` alone for the core report API and custom adapters. The `pandas`, `altair`, `matplotlib`, and `plotly` extras can also be installed separately. Offline Altair embedding requires `reportkit[offline]`.

## Quick start

```python
from datetime import date

import altair as alt
import pandas as pd
from matplotlib.figure import Figure
import plotly.graph_objects as go

from reportkit import HTMLWriter, Report

sales = pd.DataFrame({"month": ["Jan", "Feb"], "revenue": [120, 145]})
chart = alt.Chart(sales).mark_bar().encode(x="month:N", y="revenue:Q")
figure = Figure(figsize=(5, 2.5))
figure.subplots().plot([1, 2], [120, 145])
plot = go.Figure(data=go.Bar(x=["Jan", "Feb"], y=[120, 145]))

report = Report("Sales analysis", description="Monthly revenue", author="Analyst", date=date.today())
report.heading(1, "Sales analysis")
report.heading(2, "Summary")
report.markdown("Revenue **increased** in February.")
report.unordered(["January: 120", "February: 145", ["Increase: 25"]])
report.add(sales.style.format({"revenue": "${:.2f}"}), caption="Revenue by month")

with report.section("Trends"):
    with report.columns(2):
        report.add(chart, caption="Interactive chart")
        report.add(figure, caption="Static figure")
    report.add(plot, caption="Plotly view")

HTMLWriter().write(report.document, "sales.html")
```

## Complete showcase

Run [examples/report_showcase.py](examples/report_showcase.py) after installing the `all` extra:

```bash
python -m pip install -e '.[all]'
python examples/report_showcase.py
```

It writes `examples/report_showcase.html` and demonstrates formatted tables, Altair, Matplotlib, Plotly, nested lists, raw HTML, columns, and report concatenation. Comments marked `# todo:` identify features used by the reference showcase that reportkit does not support yet.

`Report.to_html()` and `Report.write(path)` are shortcuts using the default writer. The title passed to `Report(...)` becomes the browser page title. Without one, the writer uses the first rendered heading, or `Report` when there is no heading. The page title does not add a visible heading. The writer also supports reusable body content:

```python
fragment = HTMLWriter().render(report.document, fragment=True)
```

The fragment includes scoped CSS and the report body, without an HTML document wrapper. Pandas tables and Matplotlib images are embedded in the output. [Altair charts](https://altair-viz.github.io/user_guide/saving_charts.html) and [Plotly figures](https://plotly.com/python-api-reference/generated/plotly.io.to_html.html) load JavaScript from a CDN, so viewers need network access and a host that permits scripts. For a single HTML file with Altair dependencies embedded, install `reportkit[offline]` and use `HTMLWriter(inline_altair=True)`. Altair charts that reference external data URLs still need access to those URLs. Documentation platforms may strip scripts or styles from pasted HTML.

## API notes

- `Report(title, description=..., author=..., date=...)` stores optional metadata. The title sets the browser page title.
- `heading(level, title)` accepts levels 1 through 6.
- `markdown(content)` and `paragraph(text)` render Markdown with raw HTML escaped.
- `list(items, ordered=False)`, `ordered(items)`, and `unordered(items)` accept strings and nested lists. A nested list follows its parent item and inherits the outer list style; item text is escaped.
- `raw_html(content)` and `add(string)` insert trusted HTML without escaping. Raw strings cannot have captions.
- `add(value, caption=None)` stores non-string artifacts until rendering.
- `concat(other)` and `+` return a new report with both reports' content and the left report's metadata. The node tree is copied, while artifact objects remain shared.
- `section(title)` and `columns(count)` are context managers. Every direct child of a columns block is one grid item; additional items wrap to the next row.

Unsupported artifacts raise `TypeError` during rendering. To support another type, register an adapter that returns `RenderedArtifact(html=...)`:

```python
from reportkit import AdapterRegistry, HTMLWriter, RenderedArtifact

class MyAdapter:
    def render(self, value):
        return RenderedArtifact(f"<pre>{value.safe_html}</pre>")

registry = AdapterRegistry()
registry.register(MyArtifact, MyAdapter())
writer = HTMLWriter(registry=registry)
```

Adapter HTML and raw HTML nodes are trusted output and are inserted without escaping. Escape untrusted content in custom adapters and raw HTML strings.

## Development

```bash
make test
make build
```

`make test` uses the standard library test runner. Integration tests for Pandas, Altair, Matplotlib, and Plotly run when those packages are installed. `make build` requires the Python `build` package.

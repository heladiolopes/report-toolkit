# reportkit

Compose analytical reports in Python, then render them as styled HTML. A report stores its document structure until you ask a writer to render it.

## Install

```bash
python -m pip install -e '.[all]'
```

Install `reportkit` alone if you only need the document model and custom adapters. The `pandas`, `altair`, and `matplotlib` extras can also be installed separately. Offline Altair embedding requires `reportkit[offline]`.

## Quick start

```python
from datetime import date

import altair as alt
import pandas as pd
from matplotlib.figure import Figure

from reportkit import HTMLWriter, Report

sales = pd.DataFrame({"month": ["Jan", "Feb"], "revenue": [120, 145]})
chart = alt.Chart(sales).mark_bar().encode(x="month:N", y="revenue:Q")
figure = Figure(figsize=(5, 2.5))
figure.subplots().plot([1, 2], [120, 145])

report = Report("Sales analysis", description="Monthly revenue", author="Analyst", date=date.today())
report.heading(2, "Summary")
report.markdown("Revenue **increased** in February.")
report.list(["January: 120", "February: 145"])
report.add(sales.style.format({"revenue": "${:.2f}"}), caption="Revenue by month")

with report.section("Trends"):
    with report.columns(2):
        report.add(chart, caption="Interactive chart")
        report.add(figure, caption="Static figure")

HTMLWriter().write(report.document, "sales.html")
```

`Report.to_html()` and `Report.write(path)` are shortcuts using the default writer. The writer also supports reusable body content:

```python
fragment = HTMLWriter().render(report.document, fragment=True)
```

The fragment includes scoped CSS and the report body, without an HTML document wrapper. Pandas tables and Matplotlib images are embedded in the output. [Altair charts](https://altair-viz.github.io/user_guide/saving_charts.html) use JavaScript loaded from a CDN by default, so viewers need network access and a host that permits scripts. For a single HTML file with Altair dependencies embedded, install `reportkit[offline]` and use `HTMLWriter(inline_altair=True)`. Altair charts that reference external data URLs still need access to those URLs. Documentation platforms may strip scripts or styles from pasted HTML.

## API notes

- `Report(title, description=..., author=..., date=...)` stores optional metadata.
- `heading(level, title)` accepts levels 1 through 6.
- `markdown(content)` renders Markdown with raw HTML escaped.
- `list(items, ordered=False)` accepts strings as items; item text is escaped.
- `add(value, caption=None)` stores the original object until rendering.
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

Adapter HTML is trusted output and is inserted without escaping. Escape untrusted content in custom adapters.

## Development

```bash
make test
make build
```

`make test` uses the standard library test runner. Integration tests for Pandas, Altair, and Matplotlib run when those packages are installed. `make build` requires the Python `build` package.

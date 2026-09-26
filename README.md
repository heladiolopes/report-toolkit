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
report.heading(2, "Summary")
report.markdown("Revenue **increased** in February.")
report.unordered(["January: 120", "February: 145", ["Increase: 25"]])
report.add(sales.style.format({"revenue": "${:.2f}"}), caption="Revenue by month")

report.heading(2, "Trends")
with report.columns(2):
    with report.panel("Interactive trend"):
        report.add(chart, caption="Interactive chart")
    with report.panel("Static trend"):
        report.add(figure, caption="Static figure")
report.add(plot, caption="Plotly view")

HTMLWriter(toc=True, toc_depth=2).write(report.document, "sales.html")
```

## Markdown templates

Separate recurring report narrative from Python analysis with
`Report.from_template(path, context=...)` or
`Report.from_template_string(source, context=...)`. Templates support literal
text variables, analytical artifacts with captions, headings, columns, and panels.
YAML metadata requires the optional `templates` extra (also included in `all`).

See the [template guide](docs/markdown-templates.md) and run
`uv run --extra all python examples/template_report.py` for a complete example.

## Complete showcase

Run [examples/report_showcase.py](examples/report_showcase.py) after installing the `all` extra:

```bash
python -m pip install -e '.[all]'
python examples/report_showcase.py
```

It writes `examples/report_showcase.html` and demonstrates formatted tables, Altair, Matplotlib, Plotly, nested lists, raw HTML, titled panels, automatic heading sections, a table of contents, and report concatenation. Comments marked `# todo:` identify features used by the reference showcase that reportkit does not support yet.

Both examples print the composer tree to the terminal before writing HTML. Use `print(report.to_tree())` to inspect any report's structure, including nested lists, text previews, and artifact types and captions.

`Report.to_html()` and `Report.write(path)` are shortcuts using the default writer. The title passed to `Report(...)` appears at the top of the page and sets the browser tab title. Description and metadata follow, then the optional table of contents, then all report content. Without an explicit title, there is no visible report title and the browser tab uses `Report`; content headings are never used to infer a title. The writer also supports reusable body content:

```python
fragment = HTMLWriter().render(report.document, fragment=True)
```

The fragment includes scoped CSS and the report body, without an HTML document wrapper. Pandas tables and Matplotlib images are embedded in the output. [Altair charts](https://altair-viz.github.io/user_guide/saving_charts.html) and [Plotly figures](https://plotly.com/python-api-reference/generated/plotly.io.to_html.html) load JavaScript from a CDN, so viewers need network access and a host that permits scripts. For a single HTML file with Altair dependencies embedded, install `reportkit[offline]` and use `HTMLWriter(inline_altair=True)`. Altair charts that reference external data URLs still need access to those URLs. Documentation platforms may strip scripts or styles from pasted HTML.

## API notes

- `Report(title, description=..., author=..., date=...)` stores optional metadata. The title is the single conceptual level-0 report title, displayed above the TOC and excluded from it. It remains document metadata, not a section; `heading(0, ...)` is invalid. Reports may have any number of level-1 sections.
- `heading(level, title, normalize=False)` accepts levels 1 through 6 and returns a `Section`. Following content belongs to that section until an equal or shallower heading starts. Larger level numbers create subsections (h2 within h1); equal numbers create siblings, and smaller numbers return to the nearest lower-numbered ancestor or the current context root. Skipped levels do not create intermediate sections. `normalize=True` replaces hyphens and underscores with spaces, collapses whitespace, and applies title case (`this-is_an-id` becomes `This Is An Id`). By default, spelling and acronyms are preserved.
- `markdown(content)` and `paragraph(text)` render Markdown with raw HTML escaped.
- `list(items, ordered=False)`, `ordered(items)`, and `unordered(items)` accept strings and nested lists. A nested list follows its parent item and inherits the outer list style; item text is escaped.
- `raw_html(content)` and `add(string)` insert trusted HTML without escaping. Raw strings cannot have captions.
- `add(value, caption=None)` stores non-string artifacts until rendering.
- `concat(other)` and `+` return a new report with both reports' content and the left report's metadata. The node tree is copied, while artifact objects remain shared. Existing heading groups are preserved without regrouping across report boundaries.
- `section(title)`, `columns(count)`, and `panel(title)` are context managers. Each isolates automatic heading grouping and restores the previous position on exit. An explicit section's heading is one level deeper than its enclosing heading or section (default 2, maximum 6).
- Every direct child of a columns block is one grid item; additional items wrap to the next row. A panel groups multiple elements into one item with a title above its content and horizontal scrolling for wide content. Panels also work outside columns; their titles are labels, not document headings.
- `HTMLWriter(toc=True, toc_depth=6)` adds a nested table of contents after metadata. It includes section titles up to the specified absolute level, whether created through `heading()` or `section()`. Every eligible section is included, even when its title matches the report title. TOC links target content sections, never the report title. Markdown, raw HTML, artifact internals, and panel labels are excluded. Empty contents are omitted. Headings receive deterministic, unique anchors within each render.
- `Report.to_html(toc=True, toc_depth=2)` and `Report.write(path, toc=True, toc_depth=2)` expose the same options, including with `fragment=True`.

Both `heading(...)` and `section(...)` create the same backend `Section`, storing `title`, `level`, and `children`. There is no backend `Heading` node or export. For direct model construction, use `Section(title, level=2)`; the level is keyword-only and defaults to 2. The public tree and `to_tree()` output contain sections and their content. For example, use another level-2 heading to start a sibling of a level-2 heading; opening `section(...)` there creates a subsection.

Successful writes emit one INFO record through `reportkit.writer` with the destination path and actual file size in readable units (for example, `4.2 KiB` or `1.5 MiB`). The library does not configure logging. To see these messages in an application:

```python
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
report.write("sales.html", toc=True)
```

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

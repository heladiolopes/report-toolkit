# report-toolkit

Build analytical reports in Python or Markdown templates and export styled HTML
with tables, charts, sections, and column layouts.

## Install

Install the package:

```bash
pip install report-toolkit
```

From a checkout:

```bash
uv sync
```

For tables, charts, and YAML template metadata, use `uv sync --extra all`.
Individual extras are `pandas`, `altair`, `matplotlib`, `plotly`, and `templates`;
`offline` additionally supports embedding Altair's JavaScript.

## Quick start

```python
from report_toolkit import Report

report = Report('Sales review', author='Report author')
report.heading(1, 'Summary')
report.markdown('Revenue **increased** this month.')
report.unordered(['Review the results', 'Plan the next month'])
report.write('sales.html', toc=True)
```

Open `sales.html` in a browser.

## Documentation

Start with [Getting Started](docs/getting-started.md), use
[Common Tasks](docs/common-tasks.md) for recipes, and consult the
[API Reference](docs/api-reference.md) for signatures and constraints.
See the [Changelog](CHANGELOG.md) for release history and upcoming changes.

## Two equivalent examples

[Python composition](examples/sales_report.py) and
[Markdown templates](examples/template_report.py), using
[monthly_sales.md](examples/monthly_sales.md), generate the same sales report.
They demonstrate shared text, list, table, chart, and layout capabilities.

```bash
uv run --extra all python examples/sales_report.py
uv run --extra all python examples/template_report.py
```

Each prints its report tree and output path. Open `examples/sales_report.html`
and `examples/template_report.html` in a browser. Altair and Plotly charts
require network access for their JavaScript. Raw HTML is covered in the
[recipes](docs/common-tasks.md#insert-trusted-html), since templates escape it.

## Themes

Export with `style={'mode': 'dark'}`, or use `style={'mode': 'auto'}` to follow
the reader's system appearance. Choose `slate`, `azure`, `parchment`, or `ember`
with `style={'palette': 'parchment'}`. The default preserves the previous light
appearance. Define reusable `Style`, `Theme`, and `Palette` objects;
see [Themes](docs/themes.md) for customization and migration from `theme=`, and the
[theme gallery](examples/theme_gallery.py).

## Rendering profiles

Use `profile='rich'` (the default) for interactive reports, `profile='portable'`
for static SVG charts, or `profile='content'` for a content fragment with minimal
layout CSS and interactive charts. Install `portable` for SVG exporters;
Plotly also requires Chrome at export time. Derive immutable profiles with
`get_profile(...).with_overrides(...)`, including HTML tag-to-class mappings for
host applications. See [Rendering profiles](docs/rendering-profiles.md).

## Development

```bash
uv run --extra all pytest
uv run --extra all make test
uv run ruff check .
uv run ruff format --check .
uv run make build
```

`make test` and pytest both run the unittest-compatible suite, including the
example integration test. Optional integration tests skip when dependencies are absent.
Version tags run tests, Ruff lint, and a format check before the release workflow
builds and publishes to PyPI.

Theming code lives in `src/report_toolkit/themes/`: structural defaults belong in
`theme.py`, color values in `palette.py`, and configuration normalization in
`style.py`. Edit `src/report_toolkit/resources/report.css` for static report CSS;
HTML-specific scoping and dynamic style generation live in the writer. CSS is
packaged with the library and embedded in exported HTML. After changing resources
or package-data settings, run `make build` and verify the built distributions.

Artifact layout is configurable per item:

```python
report.add(table, center=True)
report.add(chart, width='full', expand='always')
report.write('report.html', pretty=True)  # Compact markup is the default.
```

Tables and charts use native width by default and display their full height.
Artifacts that overflow horizontally offer a bottom-right Expand button opening
a centered expanded view with zoom controls and a Close icon. Zoom is available
only in the expanded preview.
See [artifact options](docs/api-reference.md#analytical-artifacts) for details.


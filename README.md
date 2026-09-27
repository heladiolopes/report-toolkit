# reportkit

Build analytical reports in Python or Markdown templates and export styled HTML
with tables, charts, sections, and column layouts.

## Install

From a checkout:

```bash
uv sync
```

For tables, charts, and YAML template metadata, use `uv sync --extra all`.
Individual extras are `pandas`, `altair`, `matplotlib`, `plotly`, and `templates`;
`offline` additionally supports embedding Altair's JavaScript.

## Quick start

```python
from reportkit import Report

report = Report('Sales review', author='Analytics team')
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

Theming code lives in `src/reportkit/themes/`: structural defaults belong in
`theme.py`, color values in `palette.py`, and configuration normalization in
`style.py`. Edit `src/reportkit/resources/report.css` for static report CSS;
HTML-specific scoping and dynamic style generation live in the writer. CSS is
packaged with the library and embedded in exported HTML. After changing resources
or package-data settings, run `make build` and verify the built distributions.

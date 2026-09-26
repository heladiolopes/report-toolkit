# Markdown templates

Templates are an alternative to Python composition: both create a `Report` document and use the same writers and adapters. Analytical objects stay unrendered until you request output.

```python
from reportkit import Report

report = Report.from_template(
    'monthly_sales.md',
    context={'growth': '20.8%', 'revenue_table': sales.style, 'chart': figure},
    title='Monthly Sales',
)
report.write('monthly_sales.html', toc=True)
```

Use `Report.from_template_string(source, context=...)` for in-memory text. File templates use UTF-8. Both constructors accept `title`, `description`, `author`, and `date`, just like `Report()`. Returned reports support the usual composition methods; additional content starts at the document root.

## Narrative and analytical objects

```markdown
# Summary

Revenue increased by **{{ growth }}**.

{{ revenue_table }}

{% artifact chart caption="Monthly revenue" %}
```

Variables use simple context keys such as `growth` or `revenue_table`. Strings, integers, floats, decimals, booleans, and dates can appear in prose, headings, list items, and link labels. Dates use ISO format; other scalars use their string representation. Format currencies, percentages, and other presentation values in Python.

Inserted scalars are literal text: Markdown punctuation and HTML delimiters are escaped. Narrative whitespace is collapsed to single spaces. Author formatting in the template itself. Values are substituted once and cannot introduce template instructions.

Other Python objects require a placeholder on its own line, outside lists and blockquotes. Each occurrence creates a separate artifact node referencing the original object. Unsupported object types fail when the writer resolves their adapter, just as with `report.add()`.

The optional artifact tag supports captions, including scalar variables:

```markdown
{% artifact chart caption="Revenue for {{ period }}" %}
```

Tags occupy their own lines. Captions and panel titles use JSON-style double-quoted strings; use `\"` for a quote inside a string. Code blocks, inline code, and raw HTML syntax are not template instructions. Escape an opening delimiter to display it literally: `\{{ name }}` or `\{% columns 2 %}`.

Missing variables, `None` values, unsupported expressions, inline artifacts, and malformed tags raise `TemplateError`, a `ValueError` subclass, with the source filename (or `<template>`) and line number. Unused context keys are permitted. Variables in link destinations, link attributes, and reference definitions are unsupported.

## Headings and layouts

Markdown headings create sections, including underlined Setext headings. They appear in the tree and table of contents. Section titles are plain text: heading emphasis and link markup contribute their text, not formatting. The first heading does not become the report title. Headings inside lists and blockquotes stay ordinary Markdown.

```markdown
{% columns 2 %}
{% panel "Revenue for {{ period }}" %}
{{ revenue_chart }}

Narrative accompanying the chart.
{% endpanel %}
{% panel "Costs" %}
{{ costs_chart }}
{% endpanel %}
{% endcolumns %}
```

Layouts follow the Python API: each immediate child of a columns block is a grid item, while a panel groups several elements into one item. Adjacent prose blocks are kept together in one Markdown node. Column counts are positive integer literals. Layouts may nest; closing tags must match the most recent opening tag. Headings inside a layout stay within that scope.

Ordinary Markdown, including lists, blockquotes, code, and reference-style links, remains Markdown in the document. Reference definitions are shared across structural boundaries.

## YAML metadata

Install the optional parser with `uv pip install 'reportkit[templates]'` (also included in `reportkit[all]`). Without front matter, templates require no extra dependency.

```markdown
---
title: Monthly Sales
description: Revenue and costs
author: Analytics
date: 2026-09-26
---

# Summary
```

Front matter must be an initial block delimited by `---`. Only `title`, `description`, `author`, and `date` are supported. Duplicate keys, unknown keys, invalid types, and unsafe YAML tags are rejected. Metadata is not interpolated. Explicit constructor arguments override front matter; passing `None` clears a value.

## Scope and example

Templates do not evaluate Python or provide loops, conditionals, filters, attribute access, indexing, includes, or Markdown-valued substitutions. Use Python to prepare the context and the composition API for additional programmatic structure.

Run the complete example:

```bash
uv run --extra all python examples/template_report.py
```

It reads `examples/monthly_sales.md` and writes `examples/template_report.html` with a table, chart, panels, and table of contents.

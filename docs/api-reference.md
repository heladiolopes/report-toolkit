# API Reference

Import `Report`, `HTMLWriter`, and `TemplateError` from `reportkit`. This reference
covers composition and HTML output. Internal document types and adapter extension
machinery are outside its scope. See [Common Tasks](common-tasks.md) for recipes.

## Report

```python
Report(title=None, *, description=None, author=None, date=None)
```

Creates an empty report. `title`, `description`, and `author` accept strings or
`None`; `date` accepts `datetime.date`, `datetime.datetime`, a string, or `None`.
Invalid metadata types raise `TypeError`.

The title is displayed above metadata and the optional TOC and supplies the
browser tab title. It is not a section and is excluded from the TOC. An omitted
title produces no visible report title and a browser title of `Report`; content
headings never supply a fallback. `report.document` is the document accepted by
`HTMLWriter`; direct model construction is not covered here.

### Headings and text

| Signature | Behavior and return value |
| --- | --- |
| `heading(level, title, *, normalize=False)` | Starts and returns a section. `level` is an integer 1–6; `title` is a string. |
| `markdown(content)` | Appends and returns a Markdown content node; `content` must be a string. |
| `paragraph(text)` | Alias behavior for `markdown(text)`; returns the appended Markdown node. |
| `raw_html(content)` | Appends and returns trusted, unescaped HTML; `content` must be a string. |

Following content belongs to the current heading until an equal or shallower
heading begins within that scope. Deeper levels nest; skipped levels do not
create intermediate sections. `normalize=True` replaces underscores and hyphens
with spaces, collapses whitespace, and applies title case. Otherwise spelling
is preserved. Invalid levels (including booleans) raise `ValueError`; non-string
titles/content and non-boolean `normalize` raise `TypeError`.

Markdown supports standard text, links, lists, blockquotes, code, and separators;
raw HTML is escaped. Markdown headings render but do not create structural
sections or TOC entries when passed directly to `markdown()`.

### Lists

```python
report.list(items, *, ordered=False)
report.ordered(items)
report.unordered(items)
```

Each appends and returns a list node. `items` is an iterable of strings and nested
lists or tuples. A nested list must immediately follow a string parent item and
inherits the outer list style. Strings are escaped, not interpreted as Markdown.

`ordered` must be a boolean. Invalid item types or a string passed as the entire
iterable raise `TypeError`; a nested list without a preceding string raises
`ValueError`.

```python
report.unordered(['Revenue', ['January', 'February'], 'Costs'])
```

### Analytical artifacts

```python
report.add(value, *, caption=None)
```

For non-strings, stores the object and returns an artifact node. Supported
integrations are Pandas DataFrame and Styler, Altair charts, Matplotlib figures,
and Plotly figures, with their optional dependencies installed. Objects are
rendered at output time; unsupported types raise `TypeError` during rendering.

`caption` is a string or `None`, rendered as escaped text below the artifact.
Invalid caption types raise `TypeError`. A string `value` inserts trusted HTML
and returns an HTML node; any non-`None` caption then raises `ValueError`.

### Layout contexts

| Signature | Context behavior |
| --- | --- |
| `section(title)` | Yields the created section. Its level is one deeper than the nearest enclosing section, starting at 1 at the root and capped at 6. |
| `columns(count)` | Yields a columns container. Each immediate child is one grid item; additional items wrap. |
| `panel(title)` | Yields a panel grouping content beneath a label. Works inside or outside columns. |

Use each with `with report.section('Results'):` or the corresponding method.
All restore the previous composition position on exit, including after an
exception. Headings created inside a context stay in that scope. Titles must be
strings (`TypeError` otherwise). Column counts must be positive integers,
excluding booleans (`ValueError` otherwise). Panel labels are not section headings.

### Combining reports

```python
report.concat(other)
report + other
```

Returns a new report containing left then right content, preserving the left
report's metadata. Neither source is modified. Structure is copied while
artifact objects remain shared. Heading groups retain their existing boundaries.
`other` must be a `Report`, otherwise `TypeError` is raised.

### Inspection and output

```python
report.to_tree() -> str
report.to_html(*, fragment=False, toc=False, toc_depth=6, numbered_headings=False, toc_position='top', style=None) -> str
report.write(path, *, fragment=False, toc=False, toc_depth=6, numbered_headings=False, toc_position='top', style=None) -> pathlib.Path
```

`to_tree()` formats the hierarchy, abbreviated text, lists, and artifact types
and captions without rendering analytical objects.

`to_html()` renders a complete HTML document by default. `fragment=True` returns
scoped CSS and the report body without the HTML document wrapper.

`write()` renders UTF-8 HTML to a string or `Path` destination and returns that
path. Existing files are overwritten; parent directories are not created.
Filesystem and rendering errors propagate. Successful writes emit an INFO
message through `reportkit.writer` with the destination and actual file size.

`toc` must be a boolean (`TypeError` otherwise). `toc_depth` must be an integer
1–6, excluding booleans (`ValueError` otherwise), even if the TOC is disabled.
The TOC includes structural section headings up to this absolute level. Report
titles, panel labels, and Markdown/artifact-internal headings are excluded.
Empty TOCs are omitted. Section anchors are unique and deterministic per render.

`numbered_headings=True` adds hierarchical numbers (`1.`, `1.1.`, `2.`) to
structural headings and matching TOC entries. Numbering defaults to off, works
without a TOC, and does not change anchors or the document model. Skipped heading
levels do not introduce zero components. The value must be a boolean
(`TypeError` otherwise).

`toc_position` accepts `'top'` (default) or `'sidebar'` (`ValueError`
otherwise), even when `toc=False`. With a top TOC, every structural heading
includes an ↑ backlink, including headings beyond `toc_depth`. No backlinks
are rendered if the TOC is empty or disabled.

The sidebar sits outside the main content card, remains sticky on wide screens,
and scrolls independently when its entries exceed the viewport height. Below
1100px it moves above the card and remains fully visible, scrolling naturally
with the page. No toggle or JavaScript is needed. Print output also shows the
complete TOC without scroll limits. These options work with `fragment=True`.

## Template constructors

```python
Report.from_template(path, *, context=None, title=..., description=..., author=..., date=...)
Report.from_template_string(source, *, context=None, title=..., description=..., author=..., date=...)
```

Both return a `Report`. `path` is a string or `Path` to a UTF-8 file; `source` is
Markdown template text. File errors propagate. `context` is a mapping of simple
variable names to values; omission means an empty context.

The `...` notation above means “argument omitted”, not a literal default to pass.
Omitted metadata comes from front matter, if present. Explicit arguments override
front matter; `None` clears a value. Metadata types follow `Report()`.
Additional Python composition after loading starts at the document root.

### Template syntax

| Syntax | Meaning |
| --- | --- |
| `{{ name }}` in narrative | Inserts a scalar as literal text. |
| `{{ chart }}` on its own line | Inserts an analytical object without a caption. |
| `{% artifact chart caption="Revenue for {{ period }}" %}` | Inserts an analytical object with an optional caption. |
| `{% columns 2 %}` … `{% endcolumns %}` | Creates a column layout. |
| `{% panel "Revenue for {{ period }}" %}` … `{% endpanel %}` | Groups content under a panel label. |

Variables use simple keys, not expressions. Strings, integers, floats, decimals,
booleans, and dates are scalar values. Dates use ISO format; other scalars use
string conversion. Format currencies and percentages in Python. Narrative
whitespace in inserted values collapses to single spaces. Markdown punctuation
and HTML delimiters are escaped; values cannot introduce template instructions
and are substituted only once. Unused context keys are allowed.

Scalars may appear in prose, headings, list items, and link labels. Variables
in link destinations, link attributes, and reference definitions are unsupported.
Non-scalar objects require their own line outside lists and blockquotes. Each
occurrence references the same original object. Unsupported artifacts fail at
rendering time, as with `add()`.

Tags must occupy their own lines. Captions and panel titles use JSON-style
double-quoted strings, including `\"` to embed a quotation mark. Column counts
are positive integer literals. Layouts may nest; closing tags must match the
most recent opening tag. Adjacent prose stays together as Markdown content, so
use panels when several prose elements should occupy a single grid cell.

Markdown headings, including Setext headings, create structural sections and
TOC entries. Their titles use plain text extracted from emphasis and links.
The first heading is not the report title. Headings inside lists or blockquotes
remain ordinary Markdown. Ordinary Markdown lists, code, links, and blockquotes
are preserved; reference definitions have document-wide scope.

Code blocks, inline code, and raw HTML syntax are not template instructions.
Raw HTML is escaped when rendered. Escape an opening delimiter to display it
literally: `\{{ name }}` or `\{% columns 2 %}`.

Templates do not support Python evaluation, loops, conditionals, filters,
attribute access, indexing, includes, or Markdown-valued substitutions.

### YAML front matter

An initial block delimited by `---` may contain `title`, `description`, `author`,
and `date`. It requires the `templates` extra, also included in `all`; templates
without front matter need no additional dependency.

```yaml
---
title: Monthly sales
description: Revenue and costs
author: Analytics
date: 2026-05-01
---
```

Metadata is not interpolated. Duplicate or unknown keys, invalid types, and unsafe
YAML tags are rejected. Explicit constructor metadata takes precedence.

### TemplateError

`TemplateError` subclasses `ValueError`. Invalid syntax, missing or `None`
variables, inline analytical objects, unsupported expressions, mismatched tags,
and invalid front matter raise it. Messages include the source filename (or
`<template>`) and line number. Missing YAML support raises `ImportError`.

## HTMLWriter

```python
HTMLWriter(*, registry=None, inline_altair=False, toc=False, toc_depth=6, numbered_headings=False, toc_position='top', style=None)
writer.render(document, *, fragment=False) -> str
writer.write(document, path, *, fragment=False) -> pathlib.Path
```

Pass `report.document` as `document`. Rendering a different type raises
`TypeError`. Output, TOC, fragment, path, and logging behavior match the `Report`
shortcuts above.

`inline_altair=True` embeds Altair JavaScript and requires the `offline` extra;
a missing embedding dependency raises `ImportError` during rendering. It does
not embed external chart data or Plotly JavaScript. By default Altair and Plotly
load JavaScript from CDNs; tables and Matplotlib images are embedded.

`registry=None` uses built-in artifact support. The custom registry extension
API is outside this reference. Combining a custom registry with
`inline_altair=True` raises `ValueError`.


## Themes

```python
Style(*, theme='default', palette='slate', mode='light')
Theme(*, name, tokens={}, css='')
theme.with_overrides(*, name, tokens=None, css=None) -> Theme
Palette(*, name, light={}, dark={})
palette.with_overrides(*, name, light=None, dark=None) -> Palette
get_theme(name) -> Theme
get_palette(name) -> Palette
```

`HTMLWriter`, `Report.to_html()`, and `Report.write()` accept `style` as a
`Style`, a mapping with the same fields, or `None`. Omitted mapping fields use
the `Style` defaults. Unknown mapping fields raise `ValueError`.
`Style.theme` accepts a name or `Theme`; `Style.palette` accepts a name or
`Palette`. `get_theme()` accepts `default`; `get_palette()` accepts `slate`,
`azure`, `parchment`, and `ember`. Modes are `light`, `dark`, and `auto`.
Automatic mode uses CSS media queries with a light fallback.

All three configuration objects are immutable. `Theme` copies and freezes its
structural tokens, filling omitted tokens from `default`. `Palette` copies and
freezes both color mappings, filling missing tokens from the corresponding
`slate` mode. Names must be nonempty strings; tokens must be mappings of supported
keys to nonempty CSS strings; theme `css` must be a string. Incorrect types raise
`TypeError`; unknown names or keys, empty names or values, and unsupported modes
raise `ValueError`. Color tokens in themes and structural tokens in palettes
are rejected. CSS syntax itself is not validated.

`with_overrides()` merges supplied token mappings, preserving omitted fields.
For themes, supplied CSS replaces the original; `css=''` clears it. Custom
objects need no global registration. `HTMLWriter.style` contains the resolved
configuration with theme and palette names replaced by objects.

This API replaces `theme=`, `AutoTheme`, `Theme.mode`, and all old preset names
without compatibility aliases. See the [migration examples](themes.md#migration).

See [Themes](themes.md) for every token, custom CSS scoping, examples, and chart
styling boundaries.

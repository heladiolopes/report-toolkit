# Rendering profiles

Choose capabilities at export without recomposing your report:

```python
report.write('rich.html')
report.write('portable.html', profile='portable')
content = report.to_html(profile='content', toc=True)
```

`HTMLWriter(profile=...)`, `Report.to_html(profile=...)`, and
`Report.write(profile=...)` accept a built-in name or a `RenderingProfile`.
The default is `rich`.

| Profile | Output | Charts | Styling and navigation |
| --- | --- | --- | --- |
| `rich` | Page or fragment | Interactive Altair and Plotly | Themes, artifact controls, top/sidebar TOC, or full-page reader |
| `portable` | Page or fragment | Static SVG for Altair and Plotly | Themes, no artifact controls, top or sidebar TOC |
| `content` | Always a fragment | Same chart HTML as rich | Minimal scoped layout CSS, no artifact controls, top TOC only |

Reader positioning requires a full page with `toc=True`; see the
[API Reference](api-reference.md#inspection-and-output) for exact profile and
fragment constraints.

All profiles preserve sections, panels, columns, captions, numbered headings,
and the existing `toc=False` default. Rich and portable render report metadata
and the visible TOC title. Content omits the report title, description, author,
date, and visible TOC title; its TOC retains its accessible label and links.
TOC positions are
validated even when `toc=False`. The `content` profile overrides `fragment=False`.
Its host supplies typography, colors, and table styling; explicit Pandas Styler
CSS remains embedded. `style` is still validated but is used only by profiles
whose `stylesheet` is `theme`.

Proportional artifact scaling requires the `rich` profile's runtime and
JavaScript enabled. In `portable` and `content`, `width='full'` uses CSS sizing:
tables reflow across the available width, and images retain their aspect ratio.
Interactive charts in `content` keep their library's sizing behavior.
Neither profile provides artifact expansion or zoom controls.

## Portable charts

Install the optional exporters:

```bash
uv sync --extra portable
```

Altair SVG export uses `vl-convert-python`. Plotly SVG export uses Kaleido v1,
Plotly 6.1.1 or later, and an installed Chrome/Chromium browser. See
[Plotly's static export guide](https://plotly.com/python/static-image-export/)
for browser setup. Rendering does not install a browser automatically.

SVG images are embedded as base64 data URLs, so exported charts need no
JavaScript or companion files. Some Plotly trace types rasterize content inside
SVG. Matplotlib continues to export embedded PNG; tables retain their formatting.
Missing exporters and export failures raise errors; interactive charts are never
used as a fallback. `inline_altair=True` cannot be combined with an SVG profile.

Portable affects the built-in adapters and report runtime. Trusted raw HTML and
custom adapter payloads remain author-controlled, including external images or
scripts they contain. It does not make arbitrary supplied HTML self-contained.

## Custom profiles and host classes

Derive a profile without registering a global name:

```python
from report_toolkit import get_profile

host_content = get_profile('content').with_overrides(
    name='host-content',
    element_classes={
        'table': ('host-table',),
        'th': ('host-header',),
        'td': ('host-cell',),
        'p': ('host-paragraph',),
    },
)
report.write('host-content.html', profile=host_content, toc=True)
```

Replace these tokens with classes recognized by your host application. The
library includes no tool-specific class names or profiles. Class additions apply
to generated structure, rendered Markdown, adapter HTML, and trusted HTML.
Existing classes are retained and additions are deduplicated. Unrelated markup,
script/style bodies, IDs, and formatting attributes are preserved. Class mapping
also applies to embedded SVG tags when an adapter returns inline SVG; built-in
portable images use data URLs, whose contents are opaque to this processing.

`RenderingProfile` is immutable and copies/freezes its class mapping:

| Field | Default | Meaning |
| --- | --- | --- |
| `name` | Required | Nonempty descriptive name |
| `chart_mode` | `'interactive'` | `'interactive'` or `'svg'` |
| `content_only` | `False` | Force fragment output |
| `include_metadata` | `True` | Render report title, description, author, and date; `False` in content |
| `include_toc_title` | `True` | Render the visible TOC title; `False` in content |
| `stylesheet` | `'theme'` | `'theme'` or minimal `'layout'` CSS |
| `artifact_controls` | `True` | Include report expansion/zoom runtime |
| `toc_positions` | `('top', 'sidebar', 'reader')` | Nonempty tuple of allowed positions |
| `element_classes` | `{}` | Lowercase HTML tag names mapped to tuples of class tokens |

SVG profiles must disable artifact controls. Class tokens must be nonempty
strings without whitespace. `with_overrides(name=..., **changes)` replaces
capability fields and merges tag mappings. Each supplied tuple replaces that
tag's inherited additions; `()` clears them. It never removes existing payload
classes. Unknown built-in names raise `ValueError`.

A content host must accept fragment CSS and chart scripts for interactive charts
to work. Browser clipboard handling, host-specific compatibility, and publishing
integrations are outside this API.

## Custom adapters

Existing adapters with `render(value) -> RenderedArtifact` continue to work for
interactive profiles. SVG profiles require explicit profile-aware support:

```python
from report_toolkit import RenderedArtifact


class MyAdapter:
    def render_for_profile(self, value, *, profile):
        if profile.chart_mode == 'svg':
            return RenderedArtifact(value.svg_html(), kind='image')
        return RenderedArtifact(value.interactive_html(), kind='custom')
```

Register it through `AdapterRegistry.register(type_or_predicate, adapter)` and
pass the registry to `HTMLWriter`. `ProfileAwareAdapter` describes this protocol;
an adapter may implement both methods, in which case `render_for_profile` takes
precedence. Adapters receive the resolved profile object and must honor its chart
mode; the writer does not inspect or sanitize returned payloads. Unsupported
exports should raise a useful error.

Run `uv run --extra portable python examples/profile_gallery.py /tmp/profile-gallery`
to export the same report under all three profiles and a custom host profile.

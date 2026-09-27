# Themes

Choose a theme when exporting; the same report can be rendered repeatedly with
different appearances. This works for both Python composition and Markdown templates.

```python
report.write('dark.html', theme='dark')
report.write('adaptive.html', theme='auto')
fragment = report.to_html(fragment=True, theme='paper')
```

| Preset | Appearance |
| --- | --- |
| `light` | White and neutral gray with Times-based typography; the default |
| `dark` | Near-black surfaces with Times-based typography and blue links |
| `paper` | Warm cream with serif typography |
| `ink` | Warm charcoal with serif typography |
| `auto` | `light` or `dark`, following the reader's system preference |
| `auto-paper` | `paper` or `ink`, following the reader's system preference |

Automatic themes use CSS `prefers-color-scheme` and fall back to light styling
when the browser does not support it. They require no JavaScript, network access,
or reader toggle. Explicit presets stay in their selected mode.

The light and dark themes use compact content spacing and bordered table cells,
with a 1040px maximum report width and 5px report corners. Page padding remains
roomy, and the TOC retains its existing typography and colors. The `paper` and
`ink` alternatives retain their warmer palettes and previous spacing.

## Define a custom theme

Start from a preset and override its tokens. Each token value is a CSS string.
Theme objects and their token mappings are immutable; deriving a theme leaves
the original unchanged.

```python
from reportkit import AutoTheme, HTMLWriter, get_theme

custom_light = get_theme('light').with_overrides(
    name='custom-light',
    tokens={'accent': '#2457a7', 'content_width': '1120px'},
    css='& .report-title { letter-spacing: -.04em; }',
)
custom_dark = get_theme('dark').with_overrides(
    name='custom-dark',
    tokens={'accent': '#91baff', 'content_width': '1120px'},
    css='& .report-title { letter-spacing: -.04em; }',
)

writer = HTMLWriter(theme=AutoTheme(light=custom_light, dark=custom_dark))
writer.write(report.document, 'custom.html')
```

You can also construct `Theme(name='custom', tokens={...}, css='...')` directly.
Omitted tokens inherit the default light theme. `mode='dark'` sets the browser's
color scheme; it does not supply a dark palette. Derive from `get_theme('dark')`
or `get_theme('ink')` for dark defaults.

`with_overrides(name=..., tokens=None, css=None)` retains the original mode,
merges supplied tokens, and inherits CSS when omitted. Supplied CSS replaces the
original CSS; use `css=''` to remove it. An `AutoTheme` requires two `Theme`
objects with matching `light` and `dark` modes. No global registration is needed.

## Tokens

Inspect `get_theme('light').tokens` for the full default values. All supported
keys are listed below; unknown keys raise `ValueError` to catch spelling mistakes.

| Tokens | Controls |
| --- | --- |
| `page_background` | Full-document background; never applied to a fragment's host page |
| `background`, `surface` | Report background and secondary surface color |
| `text`, `heading`, `accent` | Body text, headings, links and blockquote borders |
| `description`, `muted` | Description, metadata and captions |
| `border`, `table_header`, `shadow_color` | Rules, header backgrounds and page shadow color |
| `font_family`, `code_font` | Body and code font stacks |
| `font_size`, `line_height` | Base text size and unitless line height |
| `content_width`, `page_margin`, `content_padding`, `radius` | Page sizing, whitespace and corner radius |
| `h1_size`, `h2_size`, `h3_size`, `h4_size`, `h5_size`, `h6_size` | Section heading sizes |
| `section_spacing`, `column_gap` | Section separation and column gutters |
| `caption_size`, `figure_margin` | Caption text size and figure spacing |
| `table_size`, `cell_padding` | Table font size and cell whitespace |
| `panel_background`, `panel_padding` | Panel surfaces and internal spacing |
| `shadow_geometry` | Shadow offsets and blur, combined with `shadow_color` |
| `title_size`, `heading_line_height`, `heading_margin` | Report title size and section heading rhythm |
| `h2_border_width`, `h2_padding` | Second-level heading rule width and bottom padding |
| `paragraph_margin`, `list_margin`, `nested_list_margin`, `list_item_spacing` | Content spacing |
| `link_decoration`, `accent_hover` | Link decoration and hover color |
| `table_border_width`, `table_line_height` | Cell borders (bottom rules remain 1px) and table line height |
| `pre_padding`, `pre_background`, `pre_radius`, `pre_margin`, `code_size` | Code block styling and code font size |
| `blockquote_margin`, `blockquote_padding`, `blockquote_border_width`, `blockquote_background` | Blockquote styling |
| `toc_font_family`, `toc_line_height`, `toc_text`, `toc_background`, `toc_accent` | Independent TOC typography and colors |

The responsive layout uses compact padding and one column below 700px. Custom
CSS can override responsive rules when necessary. Font stacks use local fonts;
the built-in themes do not download fonts.

## CSS customization and fragments

For styling beyond tokens, use the theme's `css` string. The writer replaces every
`&` with that theme's report-root selector, then places the CSS after the built-in
styles. Prefix **each selector** with `&` to keep rules within the report:

```python
custom = get_theme('paper').with_overrides(
    name='custom',
    css='& h2, & h3 { font-style: italic; }',
)
```

This is literal placeholder substitution, not Sass or CSS nesting. Within an
automatic pair, custom CSS is applied only for its corresponding mode. Token
values and custom CSS are trusted author-provided code, not sanitized user input.
CSS syntax and color contrast of custom themes are the author's responsibility.

Each theme's styles target a content-derived report attribute. Differently themed
fragments can therefore share a page without their generated theme styles
interfering. Unscoped custom CSS can still affect the host page. Existing section
anchor IDs are unchanged; repeated copies of a report can share anchor IDs.

## Tables and charts

Themes style report text, layout, ordinary tables, panels, blockquotes, and figure
captions. Explicit Pandas Styler rules retain precedence over the report defaults.
Chart colors, backgrounds, labels, and exported images retain their original
styling; configure those through the chart library. Theme selection does not
change adapter interfaces or rendering capabilities.

## Preview the themes

Run the dependency-free [theme gallery](../examples/theme_gallery.py):

```bash
uv run python examples/theme_gallery.py /tmp/reportkit-theme-gallery
```

Open the generated HTML files to compare all presets, a custom automatic pair,
and multiple differently themed fragments. Change your system appearance to
preview automatic themes in both modes.

# Themes

Choose presentation when exporting. The same report can use different styles,
whether authored in Python or loaded from a Markdown template.

```python
from reportkit import Style

report.write('dark.html', style=Style(mode='dark'))
report.write('adaptive.html', style={'palette': 'ember', 'mode': 'auto'})
fragment = report.to_html(fragment=True, style={'palette': 'parchment'})
```

`Style` has exactly three fields:

| Field | Default | Choices |
| --- | --- | --- |
| `theme` | `'default'` | Structural theme name or custom `Theme` |
| `palette` | `'slate'` | Palette name or custom `Palette` |
| `mode` | `'light'` | `'light'`, `'dark'`, or `'auto'` |

`HTMLWriter(style=...)`, `Report.to_html(style=...)`, and `Report.write(style=...)`
accept a `Style`, a mapping with the same fields, or `None`. Missing fields use
the defaults; `None`, `{}`, and `Style()` are equivalent. Unknown fields or names
raise `ValueError`. Presentation is never stored in the report's document model.

## Built-in presentation

The only built-in structural theme is `default`. It preserves the previous light
layout: 16px body text, 1.5 line height, 1040px maximum report width, 5px corners,
the report frame and shadow, compact content spacing, and bordered table cells.
Publication-style restyling is deferred. Artifact expansion controls
use the selected theme and palette.

| Palette | Appearance |
| --- | --- |
| `slate` | Previous light colors; cool dashboard grays and blue accents in dark mode |
| `azure` | Neutral gray surfaces, clear borders, and strong blue accents |
| `parchment` | Cream light surfaces, warm charcoal dark surfaces, and blue accents |
| `ember` | Warm neutral surfaces and orange accents |

Every palette provides light and dark colors. Foreground colors are adjusted
where needed to maintain at least 4.5:1 contrast against the built-in page,
report, secondary, and table-header surfaces. Custom colors are not adjusted.

`auto` emits light colors normally, switching colors and the browser's
`color-scheme` under `prefers-color-scheme: dark`. It needs no JavaScript,
network access, or reader toggle. Explicit modes stay fixed. Structure and
typography are identical across modes and palettes.

## Custom themes and palettes

Theme tokens control structure; palette tokens control colors. Derive each
independently, then combine them in a style:

```python
from reportkit import HTMLWriter, Style, get_palette, get_theme

theme = get_theme('default').with_overrides(
    name='wide',
    tokens={'content_width': '1120px'},
    css='& .report-title { letter-spacing: -.04em; }',
)
palette = get_palette('slate').with_overrides(
    name='brand',
    light={'accent': '#2457a7'},
    dark={'accent': '#91baff'},
)
writer = HTMLWriter(style=Style(theme=theme, palette=palette, mode='auto'))
writer.write(report.document, 'custom.html')
```

You can also construct `Theme(name='custom', tokens={...}, css='...')` and
`Palette(name='custom', light={...}, dark={...})` directly. Omitted theme tokens
inherit `default`; omitted palette tokens inherit the corresponding `slate` mode.
Derive from another built-in palette to inherit that palette instead.

Objects copy and freeze their mappings, so later changes to the original input
cannot change a style. `with_overrides()` returns a new object, merging supplied
tokens and inheriting omitted fields. Supplied theme CSS replaces the original;
`css=''` clears it. Theme CSS applies in both modes; use CSS media queries when
custom rules should apply only in one mode. No global registration is required.

## Tokens

Inspect `get_theme('default').tokens` and `get_palette('slate').light` / `.dark`
for complete defaults. Supported values are nonempty CSS strings. Unknown keys,
color tokens in themes, and structural tokens in palettes raise `ValueError`.
Incorrect types raise `TypeError`. CSS syntax is not validated.

### Structural theme tokens

| Tokens | Controls |
| --- | --- |
| `font_family`, `code_font`, `font_size`, `line_height` | Font stacks and base typography |
| `content_width`, `page_margin`, `content_padding`, `radius` | Report sizing and frame geometry |
| `shadow_geometry` | Shadow offsets and blur, combined with palette `shadow_color` |
| `title_size`, `title_weight`, `title_line_height` | Report title typography |
| `h1_size` through `h6_size`, `h1_weight` through `h6_weight`, `h1_line_height` through `h6_line_height` | Individual heading typography |
| `heading_line_height`, `heading_margin`, `h2_border_width`, `h2_padding` | Shared heading rhythm and second-level heading rule |
| `section_spacing`, `column_gap`, `panel_padding` | Section, column, and existing panel spacing |
| `caption_size`, `caption_line_height`, `figure_margin` | Captions, metadata, and figure spacing |
| `paragraph_margin`, `list_margin`, `nested_list_margin`, `list_item_spacing` | Prose and list spacing |
| `link_decoration` | Link decoration |
| `table_size`, `cell_padding`, `table_border_width`, `table_line_height` | Ordinary table typography and borders; bottom rules remain 1px |
| `pre_padding`, `pre_radius`, `pre_margin`, `code_size`, `code_line_height` | Code block geometry and typography |
| `blockquote_margin`, `blockquote_padding`, `blockquote_border_width` | Blockquote geometry |
| `toc_font_family`, `toc_line_height` | TOC typography, inheriting report typography by default |

### Palette tokens

| Tokens | Controls |
| --- | --- |
| `page_background` | Full-document background; never the fragment host page |
| `background`, `surface` | Report and secondary surfaces |
| `text`, `heading`, `description`, `muted` | Body text, headings, descriptions, metadata, and captions |
| `accent`, `accent_hover` | Links, hover/focus colors, and blockquote borders |
| `border`, `table_header`, `shadow_color` | Rules, table-header backgrounds, and report shadow color |
| `panel_background`, `pre_background`, `blockquote_background` | Existing component surfaces; transparent by default |
| `toc_text`, `toc_background`, `toc_accent` | TOC colors, referencing report text, surface, and accent by default |

The responsive layout uses compact padding and one column below 700px. Report
fonts prefer Roboto, then Noto Sans and sans-serif; code uses the existing local
monospace stack. Built-ins do not download fonts. The TOC inherits theme
typography, radius, and palette colors in both top and sidebar layouts. Its links
gain underlines on hover/focus and a visible outline on keyboard focus.

## CSS customization and fragments

The writer replaces every `&` in theme CSS with the report-root selector, then
places custom CSS after built-in styles and automatic-mode overrides. Prefix
**each selector** with `&` to keep rules within the report:

```python
theme = get_theme('default').with_overrides(
    name='italic-headings',
    css='& h2, & h3 { font-style: italic; }',
)
```

This is literal placeholder substitution, not Sass or CSS nesting. Token values
and custom CSS are trusted author-provided code; CSS syntax and custom color
contrast are the author's responsibility. Unscoped custom CSS can affect the
host page.

The writer resolves defaults and object overrides into structural and color
tokens, selects the mode, and applies custom CSS last. Content-derived style
identifiers scope the CSS through `data-reportkit-theme`. Differently styled
fragments can share a page without generated styles interfering. Section anchor
IDs are unchanged, so repeated reports can still share anchor IDs.

## Tables and charts

Styles control report text, layout, ordinary tables, existing panels,
blockquotes, and captions. Explicit Pandas Styler rules retain precedence.
Chart colors, backgrounds, labels, and exported images retain their original
styling; configure those through the chart library. Styling does not change
adapter interfaces, chart layout, image dimensions, or figure composition.

## Migration

This is a breaking change: `theme=`, `AutoTheme`, `Theme.mode`, and the old preset
names are removed without aliases. `get_theme()` now resolves structural themes
only; its sole built-in name is `default`.

| Previous call | Replacement |
| --- | --- |
| `report.write(path, theme='light')` | `report.write(path)` |
| `report.write(path, theme='dark')` | `report.write(path, style={'mode': 'dark'})` |
| `report.write(path, theme='auto')` | `report.write(path, style={'mode': 'auto'})` |
| `report.write(path, theme='paper')` | `report.write(path, style={'palette': 'parchment'})` |
| `report.write(path, theme='ink')` | `report.write(path, style={'palette': 'parchment', 'mode': 'dark'})` |
| `report.write(path, theme='auto-paper')` | `report.write(path, style={'palette': 'parchment', 'mode': 'auto'})` |

These replacements preserve intent, not every old preset's exact appearance.
Carbon presets have no built-in equivalent; use a custom structural `Theme` for
that typography. Split old custom tokens by ownership: geometry and fonts go in
`Theme.tokens`; colors go in `Palette.light` and `.dark`. Replace an `AutoTheme`
pair with one structural theme, a paired palette, and `Style(mode='auto')`.

## Preview styles

Run the dependency-free [gallery](../examples/theme_gallery.py):

```bash
uv run python examples/theme_gallery.py /tmp/reportkit-theme-gallery
```

It generates all 12 palette/mode combinations, a custom style, and multiple
styled fragments sharing one page. Change your system appearance to inspect
automatic modes.

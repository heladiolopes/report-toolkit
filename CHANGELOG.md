# Changelog

All notable changes to report-toolkit are documented here.
This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Removed generated theme gallery HTML from version control and ignored gallery output directories and Ruff caches; gallery generator scripts remain tracked.

### Fixed

- Template tags now support line breaks between tokens, including artifact options and layout tags.
- Expanded artifact previews now open at native size (100%), including full-width artifacts, and reset zoom on every reopening.
- Altair tooltips now appear above expanded previews and preserve their inline styling and size when zooming.

## [0.2.0] - 2026-09-30

### Added

- Rendering profiles: interactive `rich`, static SVG `portable`, and fragment `content`.
- Custom profiles, HTML class mappings, and profile-aware adapters.
- Optional `portable` extra for Altair and Plotly SVG export.
- [Profile documentation](docs/rendering-profiles.md) and [gallery](examples/profile_gallery.py).

### Changed

- Bottom-right Expand buttons, full-height artifacts, and expansion on horizontal overflow.

## [0.1.0] - 2026-09-28

### Added

- Python report composition and Markdown templates.
- HTML pages and fragments with numbered headings and tables of contents.
- Optional Pandas, Altair, Matplotlib, and Plotly integrations; custom adapters.
- Reusable themes and palettes with light, dark, and automatic modes.
- Artifact layouts, expanded previews, and zoom controls.
- Report tree visualization, documentation, and examples.

[Unreleased]: https://github.com/heladiolopes/report-toolkit/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/heladiolopes/report-toolkit/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/heladiolopes/report-toolkit/releases/tag/v0.1.0

"""Run: uv run python examples/theme_gallery.py [output-directory]."""

import argparse
from pathlib import Path

from reportkit import Report, Style, get_palette, get_theme


def build_report() -> Report:
    report = Report(
        'Theme gallery',
        description='Four color palettes in light, dark, and automatic modes.',
        author='ReportKit',
    )
    report.heading(1, 'Overview')
    report.markdown(
        'Readable **reports** with [links](#reportkit-details), `inline code`, and captions.\n\n> A note highlighted using the report’s theme.'
    )
    with report.columns(2):
        with report.panel('Highlights'):
            report.unordered(
                [
                    'Reusable themes',
                    'Light and dark palettes',
                    'System preference support',
                ]
            )
        with report.panel('Example data'):
            report.raw_html(
                '<table><thead><tr><th>Month</th><th>Revenue</th></tr></thead><tbody><tr><td>March</td><td>$12,400</td></tr><tr><td>April</td><td>$17,200</td></tr></tbody></table>'
            )
    report.heading(2, 'Details')
    report.markdown(
        '```python\nreport.write("report.html", style={"mode": "auto"})\n```'
    )
    report.raw_html(
        '<figure><svg viewBox="0 0 400 80" role="img" aria-label="Sample bars"><rect x="0" y="10" width="240" height="24" fill="#477caf"/><rect x="0" y="46" width="340" height="24" fill="#70a690"/></svg><figcaption>Chart colors remain under the author’s control.</figcaption></figure>'
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, default=Path('theme-gallery'))
    directory = parser.parse_args().output
    directory.mkdir(parents=True, exist_ok=True)
    report = build_report()
    custom_theme = get_theme('default').with_overrides(
        name='custom',
        tokens={'content_width': '1120px'},
        css='& .report-title { letter-spacing: -.04em; }',
    )
    custom_palette = get_palette('slate').with_overrides(
        name='custom',
        light={'accent': '#2457a7'},
        dark={'accent': '#91baff'},
    )
    styles = {
        f'{palette}-{mode}': Style(palette=palette, mode=mode)
        for palette in ('slate', 'azure', 'parchment', 'ember')
        for mode in ('light', 'dark', 'auto')
    }
    styles['custom'] = Style(theme=custom_theme, palette=custom_palette, mode='auto')
    for name, style in styles.items():
        report.write(directory / f'{name}.html', style=style, toc=True)
    # Also exercise differently themed fragments sharing one host page.
    fragments = ''.join(
        report.to_html(style=style, fragment=True) for style in styles.values()
    )
    (directory / 'fragments.html').write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Theme fragments</title><body>'
        + fragments
        + '</body></html>',
        encoding='utf-8',
    )
    print(f'Wrote theme gallery to {directory.resolve()}')


if __name__ == '__main__':
    main()

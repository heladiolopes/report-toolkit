"""Run: uv run python examples/theme_gallery.py [output-directory]."""

import argparse
from pathlib import Path

from reportkit import AutoTheme, Report, get_theme


def build_report() -> Report:
    report = Report(
        'Theme gallery',
        description='One report, reusable visual styles.',
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
    report.markdown('```python\nreport.write("report.html", theme="auto")\n```')
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
    themes = {
        name: get_theme(name)
        for name in ('light', 'dark', 'paper', 'ink', 'auto', 'auto-paper')
    }
    themes['custom'] = AutoTheme(light=custom_light, dark=custom_dark)
    for name, theme in themes.items():
        report.write(directory / f'{name}.html', theme=theme, toc=True)
    # Also exercise differently themed fragments sharing one host page.
    fragments = ''.join(
        report.to_html(theme=name, fragment=True)
        for name in ('light', 'dark', 'paper', 'ink')
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

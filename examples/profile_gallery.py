"""Export one report under built-in profiles and generic host classes."""

import sys
from pathlib import Path

import altair as alt

from report_toolkit import Report, get_profile


def main():
    output = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/profile-gallery')
    output.mkdir(parents=True, exist_ok=True)
    report = Report('Rendering profiles', author='Report toolkit')
    report.heading(1, 'Results')
    report.markdown('The same report can target different HTML environments.')
    with report.columns(2):
        with report.panel('Chart'):
            chart = (
                alt.Chart(
                    alt.Data(
                        values=[
                            {'month': 'Jan', 'value': 12},
                            {'month': 'Feb', 'value': 15},
                        ]
                    )
                )
                .mark_bar()
                .encode(x='month:N', y='value:Q')
            )
            report.add(chart, caption='Monthly values')
        with report.panel('Table'):
            report.raw_html(
                '<table><tr><th>Month</th><th>Value</th></tr><tr><td>Jan</td><td>12</td></tr><tr><td>Feb</td><td>15</td></tr></table>'
            )
    profiles = [get_profile(name) for name in ('rich', 'portable', 'content')]
    profiles.append(
        get_profile('content').with_overrides(
            name='host-content',
            element_classes={
                'table': ('host-table',),
                'th': ('host-header',),
                'td': ('host-cell',),
            },
        )
    )
    for profile in profiles:
        print(report.write(output / f'{profile.name}.html', profile=profile, toc=True))


if __name__ == '__main__':
    main()

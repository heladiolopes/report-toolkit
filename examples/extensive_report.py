"""Run with: uv run --extra all python examples/extensive_report.py."""

from pathlib import Path

from _extensive_data import showcase_context

from reportkit import Report


def build_report() -> Report:
    return Report.from_template(
        Path(__file__).with_suffix('.md'), context=showcase_context()
    )


def main() -> None:
    output = build_report().write(
        Path(__file__).with_suffix('.html'),
        toc=True,
        toc_position='sidebar',
        toc_depth=6,
        numbered_headings=True,
    )
    print(f'Wrote {output.resolve()}')


if __name__ == '__main__':
    main()

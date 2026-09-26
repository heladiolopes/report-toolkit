"""Run with: uv run --extra all python examples/sales_report.py."""

from datetime import date
from pathlib import Path

from _sales_data import profit_figure, revenue_chart, revenue_plot, sales_data

from reportkit import Report


def build_report() -> Report:
    sales = sales_data()
    total = f'${sales["revenue"].sum():,.0f}'
    growth = f'{sales["revenue"].iloc[-1] / sales["revenue"].iloc[0] - 1:.1%}'
    table = (
        sales.style.hide(axis='index')
        .format({'revenue': '${:,.0f}', 'cost': '${:,.0f}', 'orders': '{:,.0f}'})
        .background_gradient(subset=['revenue'], cmap='Blues')
    )
    report = Report(
        'Sales review',
        description='January–April 2026 · Illustrative data',
        author='Analytics team',
        date=date(2026, 5, 1),
    )
    report.paragraph('A review of sales performance, supporting data, and next steps.')
    with report.section('Summary'):
        report.markdown(
            f'Revenue totaled **{total}**, with *{growth} growth* from January to April. '
            'The `revenue` measure is shown before costs. '
            'See the [source data](#reportkit-source-data).'
        )
        report.unordered(
            [
                'April delivered the highest revenue.',
                ['Revenue: $17,200', 'Orders: 172'],
                'March dipped before the April recovery.',
            ]
        )
        with report.panel('Reading this report'):
            report.markdown(
                '> These figures are illustrative, not a business forecast.'
            )
            report.paragraph(
                'Tables and charts use the same four monthly observations.'
            )
    with report.section('Data'):
        with report.section('Source data'):
            report.add(sales, caption='Unformatted monthly sales data')
        with report.section('Formatted table'):
            report.add(table, caption='Revenue and costs in dollars')
    with report.section('Trends and layouts'):
        report.paragraph(
            'Three panels in two columns demonstrate wrapping to a new row.'
        )
        with report.columns(2):
            with report.panel('Revenue · Altair'):
                report.add(
                    revenue_chart(sales), caption='Monthly revenue; hover for details'
                )
                report.paragraph('April leads the period.')
            with report.panel('Profit · Matplotlib'):
                report.add(profit_figure(sales), caption='Revenue minus cost')
            with report.panel('Snapshot and notes'):
                report.add(sales[['month', 'orders']], caption='Monthly order count')
                report.unordered(['Orders track revenue.', 'Review the March decline.'])
        report.heading(2, 'Revenue and cost · Plotly')
        report.add(
            revenue_plot(sales), caption='Compare revenue and cost; toggle the legend'
        )
    with report.section('Next steps'):
        report.ordered(
            [
                'Validate the monthly inputs.',
                ['Check revenue totals.', 'Confirm costs.'],
                'Investigate the March decline.',
                'Prepare the next review.',
            ]
        )
        report.markdown(
            '---\n\nProfit is calculated consistently across the report:\n\n'
            '```python\nprofit = revenue - cost\n```'
        )
    return report


def main() -> None:
    report = build_report()
    print(report.to_tree())
    output = report.write(Path(__file__).with_suffix('.html'), toc=True, toc_depth=2)
    print(f'Wrote {output.resolve()}')


if __name__ == '__main__':
    main()

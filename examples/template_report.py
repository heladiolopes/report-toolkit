"""Run with: uv run --extra all python examples/template_report.py."""

from pathlib import Path

from _sales_data import profit_figure, revenue_chart, revenue_plot, sales_data

from reportkit import Report


def build_report() -> Report:
    sales = sales_data()
    table = (
        sales.style.hide(axis='index')
        .format({'revenue': '${:,.0f}', 'cost': '${:,.0f}', 'orders': '{:,.0f}'})
        .background_gradient(subset=['revenue'], cmap='Blues')
    )
    return Report.from_template(
        Path(__file__).with_name('monthly_sales.md'),
        context={
            'total': f'${sales["revenue"].sum():,.0f}',
            'growth': f'{sales["revenue"].iloc[-1] / sales["revenue"].iloc[0] - 1:.1%}',
            'sales': sales,
            'table': table,
            'revenue_chart': revenue_chart(sales),
            'profit_figure': profit_figure(sales),
            'orders': sales[['month', 'orders']],
            'revenue_plot': revenue_plot(sales),
        },
    )


def main() -> None:
    report = build_report()
    print(report.to_tree())
    output = report.write(Path(__file__).with_suffix('.html'), toc=True, toc_depth=2)
    print(f'Wrote {output.resolve()}')


if __name__ == '__main__':
    main()

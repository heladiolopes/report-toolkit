"""Deterministic synthetic observations and charts for the extensive use case."""

from math import pi, sin
from random import Random

import altair as alt
import pandas as pd
import plotly.graph_objects as go
from matplotlib.figure import Figure

REGIONS = ['North', 'South', 'East', 'West']
PRODUCTS = ['Essentials', 'Premium', 'Services']
COLORS = ['#3975ad', '#dc9544', '#479886', '#a468a5']


def sales_data() -> pd.DataFrame:
    rng = Random(42)
    rows = []
    for month_index, month in enumerate(
        pd.date_range('2024-01-01', periods=24, freq='MS')
    ):
        season = 1 + 0.15 * sin(2 * pi * (month_index - 2) / 12)
        for region_index, region in enumerate(REGIONS):
            for product_index, product in enumerate(PRODUCTS):
                orders = round(
                    (100 + 22 * region_index + 30 * product_index)
                    * (1 + month_index * 0.022)
                    * season
                    * rng.uniform(0.9, 1.1)
                )
                revenue = round(orders * [85, 155, 110][product_index], 2)
                cost = round(revenue * rng.uniform(0.55, 0.76), 2)
                rows.append(
                    {
                        'month': month,
                        'region': region,
                        'product': product,
                        'orders': orders,
                        'revenue': revenue,
                        'cost': cost,
                        'delivery_days': round(
                            rng.uniform(2, 5) + product_index * 0.4, 2
                        ),
                    }
                )
    data = pd.DataFrame(rows)
    data['profit'] = data['revenue'] - data['cost']
    data['margin'] = data['profit'] / data['revenue']
    return data


def totals(data: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    result = data.groupby(by, as_index=False)[
        ['revenue', 'cost', 'profit', 'orders']
    ].sum()
    result['margin'] = result['profit'] / result['revenue']
    return result


def plotly_layout(figure: go.Figure, width: int, height: int) -> go.Figure:
    figure.update_layout(
        template='plotly_white',
        width=width,
        height=height,
        colorway=COLORS,
        margin={'l': 55, 'r': 25, 't': 35, 'b': 60},
        font={'size': 11},
        legend={'orientation': 'h', 'y': -0.25},
    )
    return figure


def mpl_figure(width: int, height: int) -> Figure:
    return Figure(figsize=(width / 100, height / 100), dpi=100, layout='constrained')


def altair_charts(data, monthly, products):
    base = alt.Chart(products)
    bars = (
        base.mark_bar(color=COLORS[0])
        .encode(
            x=alt.X('product:N', title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y('revenue:Q', title='Revenue ($)'),
            tooltip=['product', alt.Tooltip('revenue:Q', format='$,.0f')],
        )
        .properties(width=280, height=220)
    )
    trend = (
        alt.Chart(monthly)
        .mark_line(point=True, color=COLORS[2])
        .encode(
            x=alt.X('month:T', title=None),
            y=alt.Y('orders:Q', title='Orders'),
            tooltip=['month:T', 'orders:Q'],
        )
        .properties(width=280, height=220)
    )
    product_months = totals(data, ['month', 'product'])
    area = (
        alt.Chart(product_months)
        .mark_area()
        .encode(
            x=alt.X('month:T', title=None),
            y=alt.Y('revenue:Q', title='Revenue ($)'),
            color=alt.Color('product:N', scale=alt.Scale(range=COLORS[:3])),
            tooltip=['month:T', 'product', alt.Tooltip('revenue:Q', format='$,.0f')],
        )
        .properties(width=640, height=360)
    )
    scatter = (
        alt.Chart(data)
        .mark_circle(size=60, opacity=0.65)
        .encode(
            x=alt.X('orders:Q', title='Orders per monthly segment'),
            y=alt.Y('margin:Q', title='Profit margin', axis=alt.Axis(format='.0%')),
            color=alt.Color('product:N', scale=alt.Scale(range=COLORS[:3])),
            tooltip=[
                'month:T',
                'region',
                'product',
                'orders',
                alt.Tooltip('margin:Q', format='.1%'),
            ],
        )
        .properties(width=640, height=360)
        .interactive()
    )
    regional = totals(data, ['month', 'region'])
    heatmap = (
        alt.Chart(regional)
        .mark_rect()
        .encode(
            x=alt.X('yearmonth(month):O', title='Month', axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('region:N', title=None),
            color=alt.Color(
                'revenue:Q', scale=alt.Scale(scheme='blues'), title='Revenue ($)'
            ),
            tooltip=['month:T', 'region', alt.Tooltip('revenue:Q', format='$,.0f')],
        )
        .properties(width=1500, height=480)
    )
    facets = (
        alt.Chart(regional)
        .mark_line(point=True, color=COLORS[0])
        .encode(
            x=alt.X('month:T', title=None),
            y=alt.Y('revenue:Q', title='Revenue ($)'),
            tooltip=['month:T', 'region', alt.Tooltip('revenue:Q', format='$,.0f')],
        )
        .properties(width=350, height=420)
        .facet(column='region:N')
    )
    return {
        'category_bars': bars,
        'order_trend': trend,
        'product_area': area,
        'margin_scatter': scatter,
        'regional_heatmap': heatmap,
        'regional_facets': facets,
    }


def plotly_charts(data, monthly, products, regions):
    donut = plotly_layout(
        go.Figure(
            go.Pie(
                labels=products['product'],
                values=products['revenue'],
                hole=0.6,
                textinfo='percent',
                marker={'colors': COLORS[:3]},
            )
        ),
        280,
        220,
    )
    donut.update_layout(showlegend=False, margin={'l': 10, 'r': 10, 't': 10, 'b': 10})
    bars = plotly_layout(
        go.Figure(
            go.Bar(
                x=regions['revenue'],
                y=regions['region'],
                orientation='h',
            )
        ),
        280,
        220,
    )
    bars.update_layout(xaxis_title='Revenue ($)')
    bubble = go.Figure()
    for index, product in enumerate(PRODUCTS):
        subset = data[data['product'] == product]
        bubble.add_scatter(
            x=subset['delivery_days'],
            y=subset['revenue'],
            mode='markers',
            name=product,
            marker={
                'size': subset['orders'],
                'sizemode': 'area',
                'sizeref': 2 * data['orders'].max() / 28**2,
                'color': COLORS[index],
                'opacity': 0.6,
            },
            text=subset['region'] + ' · ' + subset['month'].dt.strftime('%b %Y'),
            hovertemplate='%{text}<br>Delivery: %{x:.1f} days<br>Revenue: $%{y:,.0f}<extra>%{fullData.name}</extra>',
        )
    plotly_layout(bubble, 640, 360).update_layout(
        xaxis_title='Average delivery days', yaxis_title='Revenue ($)'
    )
    waterfall = plotly_layout(
        go.Figure(
            go.Waterfall(
                x=['Revenue', 'Operating cost', 'Profit'],
                measure=['absolute', 'relative', 'total'],
                y=[data['revenue'].sum(), -data['cost'].sum(), 0],
                decreasing={'marker': {'color': COLORS[1]}},
                totals={'marker': {'color': COLORS[2]}},
            )
        ),
        640,
        360,
    )
    waterfall.update_layout(yaxis_title='Amount ($)')
    grouped = go.Figure()
    for region in REGIONS:
        subset = totals(data[data['region'] == region], 'month')
        grouped.add_bar(x=subset['month'], y=subset['orders'], name=region)
    plotly_layout(grouped, 1500, 480).update_layout(
        barmode='group', yaxis_title='Orders'
    )
    trends = go.Figure()
    for column, color in zip(['revenue', 'cost', 'profit'], COLORS):
        trends.add_scatter(
            x=monthly['month'],
            y=monthly[column],
            name=column.title(),
            mode='lines+markers',
            line={'color': color},
        )
    plotly_layout(trends, 1500, 480).update_layout(
        yaxis_title='Amount ($)', hovermode='x unified'
    )
    return {
        'product_donut': donut,
        'region_bars': bars,
        'delivery_bubbles': bubble,
        'profit_waterfall': waterfall,
        'regional_orders': grouped,
        'financial_trends': trends,
    }


def matplotlib_charts(data, monthly, products):
    margin = mpl_figure(280, 220)
    ax = margin.subplots()
    ax.bar(products['product'], products['margin'] * 100, color=COLORS[:3])
    ax.set_ylabel('Profit margin (%)')
    ax.tick_params(axis='x', labelsize=8)
    histogram = mpl_figure(280, 220)
    ax = histogram.subplots()
    ax.hist(data['orders'], bins=12, color=COLORS[0], edgecolor='white')
    ax.set(xlabel='Orders per segment', ylabel='Observations')
    box = mpl_figure(640, 360)
    ax = box.subplots()
    ax.boxplot(
        [data.loc[data['region'] == region, 'delivery_days'] for region in REGIONS]
    )
    ax.set_xticks(range(1, 5), REGIONS)
    ax.set_ylabel('Average delivery days per segment')
    area = mpl_figure(640, 360)
    ax = area.subplots()
    ax.fill_between(
        monthly['month'], monthly['cost'], color=COLORS[1], alpha=0.6, label='Cost'
    )
    ax.fill_between(
        monthly['month'],
        monthly['cost'],
        monthly['revenue'],
        color=COLORS[2],
        alpha=0.6,
        label='Profit',
    )
    ax.plot(monthly['month'], monthly['revenue'], color=COLORS[0], label='Revenue')
    ax.set_ylabel('Amount ($)')
    ax.tick_params(axis='x', rotation=30)
    ax.legend(loc='upper left')
    multiples = mpl_figure(1500, 480)
    for index, (ax, region) in enumerate(
        zip(multiples.subplots(1, 4, sharey=True), REGIONS)
    ):
        subset = totals(data[data['region'] == region], 'month')
        ax.plot(
            subset['month'],
            subset['profit'],
            color=COLORS[index],
            marker='o',
            markersize=3,
        )
        ax.set_title(region)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.set_ylabel('Profit ($)' if index == 0 else '')
    heatmap = mpl_figure(1500, 480)
    ax = heatmap.subplots()
    matrix = (
        totals(data, ['month', 'region'])
        .pivot(index='region', columns='month', values='margin')
        .reindex(REGIONS)
    )
    image = ax.imshow(
        matrix.to_numpy() * 100, cmap='YlGnBu', aspect='auto', vmin=20, vmax=45
    )
    ax.set_xticks(
        range(24),
        [month.strftime('%b %y') for month in matrix.columns],
        rotation=45,
        ha='right',
    )
    ax.set_yticks(range(4), matrix.index)
    for row in range(4):
        for col in range(24):
            value = matrix.iloc[row, col] * 100
            ax.text(
                col,
                row,
                f'{value:.0f}%',
                ha='center',
                va='center',
                fontsize=8,
                color='white' if value > 35 else '#17212b',
            )
    heatmap.colorbar(image, ax=ax, label='Profit margin (%)', shrink=0.8)
    return {
        'product_margin': margin,
        'order_histogram': histogram,
        'delivery_box': box,
        'cost_area': area,
        'profit_multiples': multiples,
        'margin_heatmap': heatmap,
    }


def showcase_context() -> dict:
    data = sales_data()
    monthly = totals(data, 'month')
    products = totals(data, 'product')
    regions = totals(data, 'region')
    annual = totals(data.assign(year=data['month'].dt.year), 'year')
    context = {
        'total_revenue': f'${data["revenue"].sum():,.0f}',
        'total_profit': f'${data["profit"].sum():,.0f}',
        'total_orders': f'{data["orders"].sum():,}',
        'profit_margin': f'{data["profit"].sum() / data["revenue"].sum():.1%}',
        'annual_growth': f'{annual["revenue"].iloc[1] / annual["revenue"].iloc[0] - 1:.1%}',
        'leading_product': products.loc[products['revenue'].idxmax(), 'product'],
        'leading_region': regions.loc[regions['revenue'].idxmax(), 'region'],
        'row_count': len(data),
        'product_scorecard': products[['product', 'revenue', 'margin']]
        .rename(
            columns={'product': 'Product', 'revenue': 'Revenue', 'margin': 'Margin'}
        )
        .style.hide(axis='index')
        .format({'Revenue': '${:,.0f}', 'Margin': '{:.1%}'})
        .background_gradient(subset=['Revenue'], cmap='Blues')
        .bar(subset=['Margin'], color='#b7dfd2', vmin=0, vmax=1),
        'regional_table': regions.style.hide(axis='index').format(
            {
                'revenue': '${:,.0f}',
                'cost': '${:,.0f}',
                'profit': '${:,.0f}',
                'orders': '{:,.0f}',
                'margin': '{:.1%}',
            }
        ),
        'monthly_table': monthly.assign(month=monthly['month'].dt.strftime('%b %Y'))
        .style.hide(axis='index')
        .format(
            {
                'revenue': '${:,.0f}',
                'cost': '${:,.0f}',
                'profit': '${:,.0f}',
                'orders': '{:,.0f}',
                'margin': '{:.1%}',
            }
        ),
        'sample_table': data.head(12)
        .assign(month=lambda frame: frame['month'].dt.strftime('%b %Y'))
        .style.hide(axis='index')
        .format(
            {
                'revenue': '${:,.0f}',
                'cost': '${:,.0f}',
                'profit': '${:,.0f}',
                'margin': '{:.1%}',
                'delivery_days': '{:.2f}',
            }
        ),
    }
    context.update(altair_charts(data, monthly, products))
    context.update(plotly_charts(data, monthly, products, regions))
    context.update(matplotlib_charts(data, monthly, products))
    return context

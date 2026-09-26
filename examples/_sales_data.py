"""Shared data and chart generation for the two sales reports."""

import altair as alt
import pandas as pd
import plotly.graph_objects as go
from matplotlib.figure import Figure


def sales_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            'month': ['January', 'February', 'March', 'April'],
            'revenue': [12000, 14500, 13800, 17200],
            'cost': [8000, 9100, 8900, 10200],
            'orders': [120, 145, 138, 172],
        }
    )


def revenue_chart(sales: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(sales)
        .mark_bar()
        .encode(
            x=alt.X('month:N', sort=sales['month'].tolist(), title='Month'),
            y=alt.Y('revenue:Q', title='Revenue ($)'),
            tooltip=['month', 'revenue', 'orders'],
        )
        .properties(width='container', height=240)
    )


def profit_figure(sales: pd.DataFrame) -> Figure:
    figure = Figure(figsize=(6, 3), layout='constrained')
    axes = figure.subplots()
    axes.plot(sales['month'], sales['revenue'] - sales['cost'], marker='o')
    axes.set_ylabel('Profit ($)')
    return figure


def revenue_plot(sales: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    for column in ('revenue', 'cost'):
        figure.add_bar(x=sales['month'], y=sales[column], name=column.title())
    figure.update_layout(
        barmode='group',
        yaxis_title='Amount ($)',
        height=320,
        margin={'l': 40, 'r': 20, 't': 30, 'b': 40},
    )
    return figure

---
title: Sales review
description: January–April 2026 · Illustrative data
author: Report author
date: 2026-05-01
---

A review of sales performance, supporting data, and next steps.

# Summary

Revenue totaled **{{ total }}**, with *{{ growth }} growth* from January to April. The `revenue` measure is shown before costs. See the [source data](#reporttkt-source-data).

- April delivered the highest revenue.
    - Revenue: $17,200
    - Orders: 172
- March dipped before the April recovery.

{% panel "Reading this report" %}
> These figures are illustrative, not a business forecast.

Tables and charts use the same four monthly observations.
{% endpanel %}

# Data

## Source data

{% artifact sales caption="Unformatted monthly sales data" %}

## Formatted table

{% artifact table caption="Revenue and costs in dollars" %}

# Trends and layouts

Three panels in two columns demonstrate wrapping to a new row.

{% columns 2 %}
{% panel "Revenue · Altair" %}
{% artifact revenue_chart caption="Monthly revenue; hover for details" %}

April leads the period.
{% endpanel %}
{% panel "Profit · Matplotlib" %}
{% artifact profit_figure caption="Revenue minus cost" %}
{% endpanel %}
{% panel "Snapshot and notes" %}
{% artifact orders caption="Monthly order count" %}

- Orders track revenue.
- Review the March decline.
{% endpanel %}
{% endcolumns %}

## Revenue and cost · Plotly

{% artifact revenue_plot caption="Compare revenue and cost; toggle the legend" %}

# Next steps

1. Validate the monthly inputs.
    1. Check revenue totals.
    2. Confirm costs.
2. Investigate the March decline.
3. Prepare the next review.

---

Profit is calculated consistently across the report:

```python
profit = revenue - cost
```

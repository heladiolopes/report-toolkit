---
title: Monthly Sales
author: Analytics
---

# Summary

Revenue increased by **{{ growth }}** in {{ period }}.

{% artifact revenue_table caption="Revenue by month" %}

# Trends

{% columns 2 %}
{% panel "Revenue" %}
{{ revenue_chart }}
{% endpanel %}
{% panel "Notes for {{ period }}" %}
- The latest month generated {{ latest_revenue }} in revenue.
- Values and formatting are calculated in Python.
{% endpanel %}
{% endcolumns %}


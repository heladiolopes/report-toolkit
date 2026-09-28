---
title: The two-year trading review
description: January 2024–December 2025 · An extensive synthetic sales report
author: Report author
date: 2026-01-15
---

Twenty-four months, four regions, and three product categories tell a connected story about growth, mix, and operating performance. This report combines **Altair**, **Plotly**, and **Matplotlib** with tables and commentary, moving from a compact executive view to detailed monthly analysis.

> All observations are synthetic. This is a report-composition example, not a forecast or a description of an actual business. Customer behavior cannot be inferred from these aggregated observations.

# Executive summary

## Performance at a glance

The business generated **{{ total_revenue }}** in revenue from **{{ total_orders }} orders**, producing **{{ total_profit }}** in profit. The aggregate profit margin was **{{ profit_margin }}**. Revenue grew **{{ annual_growth }}** in 2025 compared with 2024.

{% columns 3 %}
{% panel "Revenue mix · Plotly" %}
{% artifact product_donut caption="Small · 280 × 220 px. Hover over a slice to identify its category and contribution." %}

**{{ leading_product }}** contributed the most revenue over the full period. Share of sales describes commercial mix; it does not establish which category is most efficient.
{% endpanel %}
{% panel "Profitability · Matplotlib" %}
{% artifact product_margin caption="Small · 280 × 220 px source figure. Category margins use total profit divided by total revenue." %}

Read the margin view alongside the mix chart. A high-revenue category can matter greatly to total profit even when its percentage margin is ordinary.
{% endpanel %}
{% panel "Order momentum · Altair" %}
{% artifact order_trend caption="Small · 280 × 220 px plotting area. Hover for monthly order totals." %}

The synthetic generation process combines gradual growth, recurring seasonality, and variation between segments. Individual monthly changes should be read in that context.
{% endpanel %}
{% endcolumns %}

## Questions for the review

1. How much of the sales pattern is explained by product mix?
2. Which regional differences persist across the two years?
3. Do larger volumes coincide with better margins?
4. What additional information would make an operational decision defensible?

## Reading route

Start with [Revenue](#reporttkt-revenue) for the aggregate trend, then compare products and regions. The [Detailed analysis](#reporttkt-detailed-analysis) section contains the complete monthly table and the methodology hierarchy. The sidebar includes all six heading levels.

# Business context

## Coverage and grain

The dataset contains **{{ row_count }} observations**. Each row represents one month, one region, and one product category. Orders, revenue, cost, and profit are additive at that grain. Delivery days are an illustrative segment-level average, not individual shipment observations.

{% columns 2 %}
{% panel "Commercial coverage" %}
- Period: January 2024 through December 2025.
- Regions: North, South, East, and West.
- Categories: Essentials, Premium, and Services.

Both annual periods contain twelve complete months, so the year-over-year comparison uses equal coverage.
{% endpanel %}
{% panel "Interpretation boundaries" %}
- Revenue uses a fixed illustrative price for each category.
- Costs vary as a fraction of revenue.
- There are no customer identifiers, refunds, taxes, or acquisition costs.

The word **profit** refers only to revenue minus the modeled operating cost.
{% endpanel %}
{% endcolumns %}

## Measure definitions

Revenue is the value of orders before modeled cost. Profit is revenue less cost. Aggregate margin is calculated from summed amounts, so a small segment does not receive the same weight as a large segment.

```python
profit = revenue - cost
aggregate_margin = profit.sum() / revenue.sum()
```

## Chart sizes and interaction

Small charts sit in comparison panels; medium charts provide space for distributions and relationships. Oversized charts deliberately exceed the default report content width. Altair and Plotly retain fixed widths and scroll inside their artifact containers. Matplotlib figures are embedded as images and scale down to fit.

Altair tooltips and Plotly hover, legend, and zoom controls are available when their JavaScript libraries load. Static Matplotlib figures provide a complementary, noninteractive view. The default interactive exports load their libraries from a CDN and need a network connection.

# Revenue

## Category contribution

{% columns 2 %}
{% panel "Category totals · Altair" %}
{% artifact category_bars caption="Small · 280 × 220 px plotting area. Revenue summed across both years." %}

The bar view gives a common baseline for comparing absolute revenue. **{{ leading_product }}** is the largest category by this measure.
{% endpanel %}
{% panel "What drives these totals?" %}
Category revenue reflects both order volume and the fixed category price used by the generator. The category ranking therefore cannot be interpreted as a pure measure of customer preference.

- Compare volume before discussing demand.
- Compare margin before discussing efficiency.
- Compare monthly patterns before assuming the mix is stable.
{% endpanel %}
{% endcolumns %}

## Revenue mix through time

{% artifact product_area center=true caption="Medium · Altair stacked area, 640 × 360 px plotting area. Hover to inspect a category and month." %}

The total height of the stack represents monthly revenue. The colored bands show category contributions, although only the bottom band shares a fixed baseline. Use the category totals above for precise overall comparisons.

### Seasonality and growth

The generator applies a repeating seasonal curve and a gradual upward trend to order counts. Similar shapes across categories are expected because they share those inputs. They are not independent evidence of market-wide behavior.

## Financial trajectory

{% artifact financial_trends caption="Oversized · Plotly, 1500 × 480 px. Scroll horizontally; hover for a shared monthly comparison or toggle series in the legend." %}

Revenue, cost, and profit use the same dollar axis. The gap between revenue and cost equals profit, while the profit series makes its smaller scale directly visible. Use the full two-year window to distinguish recurring movement from the underlying growth input.

# Products

## Volume and margin relationship

{% artifact margin_scatter caption="Medium · Altair scatter, 640 × 360 px plotting area. Each point is a month–region–product observation; pan or zoom to inspect clusters." %}

The scatter plot separates volume from efficiency. Margin is generated from a variable cost ratio, so a larger order count does not mechanically create a better margin. Color identifies category, and tooltips retain the observation's month and region.

### Comparing like with like

Before attributing a cluster to product performance, compare observations within a region and a similar period. The synthetic data intentionally gives categories and regions different volume baselines.

## Distribution of order volumes

{% columns 2 %}
{% panel "Order distribution · Matplotlib" %}
{% artifact order_histogram caption="Small · 280 × 220 px source figure. Counts of monthly segment observations, not counts of individual orders." %}

Each histogram entry represents an aggregate segment. Its width describes variation among those segments.
{% endpanel %}
{% panel "Distribution reading guide" %}
A histogram answers a different question from a trend line: it shows how frequently values occur, while discarding their chronological order.

A broad distribution could reflect regional scale, category mix, seasonality, or growth. It does not demonstrate unstable customer demand on its own.
{% endpanel %}
{% endcolumns %}

## Product scorecard

{% artifact product_scorecard caption="Standalone pandas styled table · Three products and three columns. Blue shading compares revenue; green bars show margin on a 0–100% scale." %}

This compact scorecard brings revenue and profitability together. Currency and percentage formatting make the units explicit, while the hidden index keeps the focus on the three business columns.

## Product review checklist

- Review contribution in dollars and margin in percent together.
- Preserve category labels when comparing observations.
- Avoid assuming a change in revenue is a change in price: category prices are fixed here.

# Regions

## Regional scale

{% columns 2 %}
{% panel "Regional revenue · Plotly" %}
{% artifact region_bars caption="Small · 280 × 220 px. Horizontal bars compare regional revenue over the complete period." %}

**{{ leading_region }}** has the largest revenue total. Regional differences partly reflect the generator's explicit volume baselines.
{% endpanel %}
{% panel "Comparison notes" %}
Scale and efficiency should be discussed separately. A large region may deliver more dollars of profit without having a higher percentage margin.

The table below preserves both views and provides exact values behind the chart.
{% endpanel %}
{% endcolumns %}

### Regional scorecard

{% artifact regional_table center=true caption="Regional totals across 24 months. Margins are weighted by revenue through the ratio of summed amounts." %}

## Monthly revenue heatmap

{% artifact regional_heatmap caption="Oversized · Altair heatmap, 1500 × 480 px plotting area. Scroll horizontally for all months; hover for exact revenue." %}

Rows retain stable region positions while columns follow time. Color provides a quick view of recurring seasonal movement. Compare values using the common legend instead of treating each row as independently scaled.

## Regional trend comparison

{% artifact regional_facets caption="Oversized · Altair faceted lines, four 350 × 420 px plotting areas plus axes and spacing. Scroll to compare all four regions." %}

The facets share a revenue scale. This preserves regional magnitude differences, while separate panels reduce line overlap. The full chart exceeds report width by design.

# Customers

## What orders can tell us

Orders provide an activity measure, but they do not identify unique customers. A repeat buyer could place several orders, and these rows contain no information that distinguishes that case from several first-time buyers.

## Regional demand proxy

{% artifact regional_orders caption="Oversized · Plotly grouped bars, 1500 × 480 px. Each monthly group compares regional order counts; scroll for the full period." %}

Use order volume as a demand proxy with the coverage caveats above. The grouped bars preserve the regional comparison within each month, and legend controls let the reader temporarily isolate regions.

### Missing customer dimensions

A real customer analysis would require stable customer identifiers, order timestamps, acquisition channels, and a definition of an active customer. Retention and lifetime value are deliberately absent from this report because the source cannot support them.

## Questions for a future customer dataset

1. What share of orders comes from returning customers?
2. Does basket value change with customer tenure?
3. Are regional patterns explained by customer count or orders per customer?

# Profitability

## From revenue to profit

{% artifact profit_waterfall caption="Medium · Plotly waterfall, 640 × 360 px. Revenue less modeled operating cost equals profit." %}

The bridge reconciles the report's principal financial measures. Costs appear as a negative contribution, and the final bar is the resulting total. It contains no additional expense categories beyond those present in the synthetic data.

## Cost coverage through time

{% artifact cost_area center=true caption="Medium · Matplotlib area figure, 640 × 360 px source. Cost and profit together fill the area below revenue." %}

The area under the revenue line is partitioned into cost and profit. Unlike two overlapping areas drawn from zero, these bands add to revenue and make the accounting relationship explicit.

### Margin versus absolute contribution

A rising profit total can coexist with an unchanged margin when revenue grows. Use the overall margin of **{{ profit_margin }}** as a whole-period reference, not as a target or a benchmark drawn from outside the dataset.

## Regional profit paths

{% artifact profit_multiples caption="Oversized source · Matplotlib small multiples, 1500 × 480 px before tight cropping. The embedded image scales to the report width." %}

All four panels share a profit axis, allowing direct magnitude comparisons. The wide source figure demonstrates how a static chart behaves differently from the horizontally scrolling interactive charts.

## Month-by-month margin map

{% artifact margin_heatmap caption="Oversized source · Matplotlib annotated heatmap, 1500 × 480 px before tight cropping. The image scales to fit; annotations show rounded margins." %}

The common color scale helps locate relatively high and low margins. Annotations are rounded for readability; calculations and totals use the unrounded values. The detailed monthly table later in the report offers another route to precise overall figures.

# Operations

## Delivery and commercial activity

{% artifact delivery_bubbles caption="Medium · Plotly bubble scatter, 640 × 360 px. Bubble area represents orders; color identifies product category." %}

Each bubble connects a segment's average delivery time with its revenue. Hover to recover the region and month. This is an exploratory display: the generator does not encode a causal relationship between faster delivery and higher revenue.

## Regional delivery distributions

{% artifact delivery_box caption="Medium · Matplotlib box plot, 640 × 360 px source. Distributions contain segment-level delivery averages." %}

These boxes summarize the spread of segment averages within each region. They do not describe the distribution of individual shipment times and should not be used to estimate shipment-level service compliance.

## Combining evidence and actions

The following three panels deliberately wrap across a two-column grid. Each groups related content so that a finding stays with its qualification and proposed follow-up.

{% columns 2 %}
{% panel "Commercial review" %}
**Observation:** {{ leading_product }} leads total category revenue.

**Qualification:** Both category price and order volume contribute to that result.

**Follow-up:** Separate volume, price, and mix in a real commercial dataset before allocating additional investment.
{% endpanel %}
{% panel "Regional review" %}
**Observation:** {{ leading_region }} contributes the most regional revenue.

**Qualification:** Regional volume baselines differ by construction.

**Follow-up:** Add market size or customer counts before comparing penetration or sales productivity.
{% endpanel %}
{% panel "Operational review" %}
**Observation:** The charts expose variation in segment delivery averages.

**Qualification:** Shipment-level tails are unavailable.

**Follow-up:** Collect individual dispatch and arrival timestamps to measure late-delivery rates.

- Agree on a service-level definition.
- Separate business days from calendar days.
- Keep the same definition across regions.
{% endpanel %}
{% endcolumns %}

# Detailed analysis

## Monthly financial table

{% artifact monthly_table caption="All 24 monthly totals. Dollar values are rounded for display; margins use unrounded aggregate amounts." %}

This table is the numerical counterpart to the wide financial trend. Use it to inspect exact monthly order counts and rounded dollar totals without relying on pointer interactions.

## Source observation sample

{% artifact sample_table caption="The first 12 observations: all region–product combinations for January 2024. The full generated dataset contains {{ row_count }} rows." %}

The sample makes the observation grain explicit. It also demonstrates a wide table alongside the oversized charts; the artifact container handles horizontal overflow when space is limited.

## Methodology

### Synthetic generation

The generator uses a fixed random seed of `42`, a regular monthly calendar, and the full region–product cross-product. Rebuilding the report produces the same observations and aggregate measures.

#### Volume and pricing

Order counts combine a regional baseline, a product baseline, a linear growth factor, a repeating seasonal factor, and bounded random variation. Values are rounded to whole orders before revenue is calculated.

##### Financial calculations

Category prices are fixed at $85 for Essentials, $155 for Premium, and $110 for Services. Modeled cost varies between 55% and 76% of revenue for each observation, with dollar amounts rounded to cents.

###### Aggregation and rounding

Sum revenue and cost first, then calculate profit and margin at the desired reporting grain. Display rounding is applied after aggregation. Never calculate the report margin by taking an unweighted average of row margins.

```python
monthly = data.groupby('month')[['revenue', 'cost', 'orders']].sum()
monthly['profit'] = monthly['revenue'] - monthly['cost']
monthly['margin'] = monthly['profit'] / monthly['revenue']
```

### Delivery measurement

Delivery days are generated separately for each monthly segment with a category-dependent offset. They are synthetic averages. Box plots treat each segment equally; no shipment-weighted service metric is claimed.

### Reproducibility and presentation

All eighteen charts and four tables use the same generated observations. Differences in chart appearance come from the chosen library, geometry, and dimensions. The wide figures are intentional examples of the report's existing overflow and image-scaling behavior.

# Recommendations

## Immediate review priorities

1. Reconcile the financial bridge with the monthly table.
2. Compare category contribution with category margin.
3. Examine regional trends using shared axes and common color scales.
4. Record the additional data needed before making customer or service-level claims.

## Next analytical iteration

Replace the synthetic generator with a validated dataset at a clearly documented grain. Add missing commercial dimensions only when their definitions are agreed. Keep the report narrative close to the evidence, especially when adding customer metrics or causal interpretations.

## Closing perspective

This example brings compact comparison panels, medium analytical charts, and deliberately oversized visuals into one long-form review. The persistent sidebar provides access to the broad business story and the deepest calculation notes, while the Markdown template keeps the narrative separate from Python chart construction.

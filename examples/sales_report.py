"""Run with `python examples/sales_report.py` after installing reportkit[all]."""

from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
from matplotlib.figure import Figure

from reportkit import HTMLWriter, Report


def main() -> None:
    sales = pd.DataFrame(
        {
            "month": ["Jan", "Feb", "Mar", "Apr"],
            "revenue": [120, 145, 138, 167],
        }
    )
    chart = alt.Chart(sales).mark_bar(color="#2563a6").encode(x="month:N", y="revenue:Q")
    figure = Figure(figsize=(5, 3))
    axes = figure.subplots()
    axes.plot(sales["month"], sales["revenue"], marker="o", color="#2563a6")
    axes.set_ylabel("Revenue")

    report = Report(
        "Sales analysis",
        description="Monthly revenue for the first four months",
        author="Analytics team",
        date=date.today(),
    )
    report.heading(2, "Summary")
    report.markdown("Revenue **increased** over the period, with a dip in March.")
    report.list(["Highest month: April", "Lowest month: January"])
    report.add(sales.style.format({"revenue": "${:.2f}"}), caption="Monthly revenue")
    with report.section("Trends"):
        with report.columns(2):
            report.add(chart, caption="Interactive view")
            report.add(figure, caption="Static view")

    output = Path("sales_report.html")
    HTMLWriter().write(report.document, output)
    print(output.resolve())


if __name__ == "__main__":
    main()

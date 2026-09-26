"""Showcase reportkit's components. Run after installing ``reportkit[all]``."""

from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import plotly.graph_objects as go
from matplotlib.figure import Figure
from pandas.io.formats.style import Styler

from reportkit import HTMLWriter, Report


OUTPUT_PATH = Path(__file__).with_name("report_showcase.html")


def monthly_weather_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            "temperature_c": [28.4, 28.1, 27.6, 26.9, 25.8, 24.7, 24.5, 25.6, 27.1, 28.3, 28.7, 28.9],
            "rainfall_mm": [182, 165, 210, 245, 188, 121, 88, 54, 32, 18, 25, 96],
        }
    )


def service_metrics_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "service": ["Auth API", "Payments API", "Search", "Recommendations", "Notifications", "Analytics"],
            "requests_per_min": [12540, 8420, 19320, 6740, 2890, 4120],
            "latency_ms": [42.5, 68.3, 35.1, 120.4, 55.2, 210.8],
            "error_rate": [0.0021, 0.0048, 0.0017, 0.0063, 0.0035, 0.0094],
            "status": ["healthy", "degraded", "healthy", "critical", "healthy", "degraded"],
        }
    )


def experiment_results_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "experiment": ["baseline", "layout A", "colors B", "copy C", "personalized D"],
            "click_rate": [0.0421, 0.0487, 0.0513, 0.0469, 0.0578],
            "conversion_rate": [0.0124, 0.0139, 0.0145, 0.0132, 0.0158],
            "sample_size": [50231, 49870, 51002, 49550, 50388],
        }
    )


def service_table() -> Styler:
    return (
        service_metrics_data()
        .style.hide(axis="index")
        .format(
            {
                "requests_per_min": "{:,.0f}",
                "latency_ms": "{:.1f} ms",
                "error_rate": "{:.2%}",
            }
        )
        .background_gradient(subset=["requests_per_min"], cmap="Blues")
        .background_gradient(subset=["latency_ms"], cmap="Oranges")
        .background_gradient(subset=["error_rate"], cmap="Reds")
        .set_caption("Service metrics formatted with pandas Styler")
    )


def service_snapshot() -> Styler:
    return (
        service_metrics_data()[["service", "status", "latency_ms", "error_rate"]]
        .style.hide(axis="index")
        .format({"latency_ms": "{:.1f} ms", "error_rate": "{:.2%}"})
        .background_gradient(subset=["latency_ms"], cmap="Oranges")
    )


def temperature_chart() -> alt.Chart:
    return (
        alt.Chart(monthly_weather_data())
        .mark_line(point=True)
        .encode(x="month:N", y="temperature_c:Q")
        .properties(height=260)
    )


def rainfall_chart() -> alt.Chart:
    return (
        alt.Chart(monthly_weather_data())
        .mark_bar()
        .encode(x="month:N", y="rainfall_mm:Q")
        .properties(height=260)
    )


def requests_figure() -> Figure:
    frame = service_metrics_data()
    figure = Figure(figsize=(7, 4))
    axes = figure.subplots()
    axes.bar(frame["service"], frame["requests_per_min"], color="#2563a6")
    axes.set_ylabel("Requests per minute")
    axes.tick_params(axis="x", rotation=25)
    figure.tight_layout()
    return figure


def health_figure() -> Figure:
    frame = service_metrics_data()
    figure = Figure(figsize=(7, 4))
    axes = figure.subplots()
    axes.plot(frame["service"], frame["latency_ms"], marker="o", label="Latency (ms)")
    axes.plot(frame["service"], frame["error_rate"] * 1000, marker="s", label="Error rate × 1000")
    axes.tick_params(axis="x", rotation=25)
    axes.legend()
    figure.tight_layout()
    return figure


def experiment_plot() -> go.Figure:
    frame = experiment_results_data()
    return go.Figure(
        data=go.Bar(x=frame["experiment"], y=frame["conversion_rate"]),
        layout={"title": "Conversion rate by experiment", "yaxis_title": "Conversion rate"},
    )


def introduction() -> Report:
    report = Report(
        "reportkit component showcase",
        description="An end-to-end example of text, tables, charts, and composition",
        author="reportkit contributors",
        date=date.today(),
    )
    report.heading(1, "reportkit component showcase")
    report.paragraph("This report demonstrates the components supported by reportkit.")
    report.markdown(
        "The same datasets appear in **tables**, *charts*, and mixed layouts. "
        "Each section is composed separately and joined with `+`."
    )
    return report


def basic_components() -> Report:
    report = Report()
    report.heading(1, "Basic components")

    with report.section("Text and formatting"):
        report.paragraph("Paragraphs use Markdown, so **emphasis** works here too.")
        report.markdown("Markdown also supports *italics*, `code`, and [links](https://example.com).")
        report.markdown("Raw tags in Markdown are escaped: <strong>not bold HTML</strong>.")
        report.raw_html('<p>This is <strong>trusted raw HTML</strong> with a custom element.</p>')
        report.unordered(["Paragraphs", "Markdown", "Raw HTML"])

    with report.section("Lists and hierarchy"):
        report.ordered(
            [
                "Load the dataset",
                ["Validate the schema", "Handle missing values"],
                "Train a model",
                ["Tune parameters", ["Grid search", "Cross-validation"]],
                "Evaluate results",
            ]
        )
        report.unordered(["Fruit", ["Apples", "Bananas", ["Green", "Yellow"]], "Vegetables"])

    with report.section("Side-by-side layout"):
        report.paragraph("A columns block places its direct children into a responsive grid.")
        # todo: Add titled side-by-side panels as a first-class component.
        with report.columns(2):
            report.add(service_snapshot(), caption="Styled service table")
            report.raw_html(
                "<div><strong>Operational summary</strong><p>Tables and commentary can share a row.</p></div>"
            )
    return report


def tables() -> Report:
    report = Report()
    report.heading(1, "Tables")
    with report.section("Pandas DataFrame"):
        report.paragraph("A DataFrame renders as a styled HTML table.")
        report.add(experiment_results_data(), caption="Experiment results")
    with report.section("Pandas Styler"):
        report.paragraph("Styler retains number formats, gradients, and its own caption.")
        report.add(service_table(), caption="Service overview")
        report.add(service_snapshot(), caption="Compact snapshot")
    # todo: Add a Great Tables adapter before including the reference showcase's GT table.
    # todo: Add an artifact name argument for stable chart and table IDs.
    return report


def charts() -> Report:
    report = Report()
    report.heading(1, "Charts")
    with report.section("Altair"):
        report.add(temperature_chart(), caption="Monthly temperature")
        with report.columns(2):
            report.add(temperature_chart(), caption="Temperature")
            report.add(rainfall_chart(), caption="Rainfall")
    with report.section("Matplotlib"):
        report.add(requests_figure(), caption="Requests per minute")
        report.add(health_figure(), caption="Service health")
    with report.section("Plotly"):
        report.add(experiment_plot(), caption="Interactive experiment chart")
    return report


def mixed_layouts() -> Report:
    report = Report()
    report.heading(1, "Mixed layouts")
    with report.section("Text and table"):
        with report.columns(2):
            report.add("<p><strong>Overview</strong></p><p>Commentary next to a styled table.</p>")
            report.add(service_snapshot(), caption="Service snapshot")
    with report.section("Chart and table"):
        with report.columns(2):
            report.add(rainfall_chart(), caption="Rainfall")
            report.add(service_table(), caption="Service metrics")
    with report.section("Chart and notes"):
        with report.columns(2):
            report.add(temperature_chart(), caption="Temperature")
            report.unordered(["January is warm", "Rainfall declines into October", "Values are illustrative"])
    with report.section("Several artifact types"):
        with report.columns(3):
            report.add(rainfall_chart(), caption="Altair")
            report.add(health_figure(), caption="Matplotlib")
            report.add(service_snapshot(), caption="Pandas Styler")
    return report


def build_report() -> Report:
    return introduction() + basic_components() + tables() + charts() + mixed_layouts()


def main() -> None:
    report = build_report()
    # todo: Add light/dark/auto themes, heading numbering, and a table of contents to HTMLWriter.
    HTMLWriter().write(report.document, OUTPUT_PATH)
    print(f"Saved report to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

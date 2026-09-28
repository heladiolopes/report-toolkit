import importlib.util
import unittest

from report_toolkit import HTMLWriter, Report


class IntegrationTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('pandas'), 'pandas is not installed')
    def test_pandas_styler_and_dataframe(self):
        import pandas as pd

        frame = pd.DataFrame({'revenue': [12, 15]})
        report = Report()
        report.add(frame.style.format({'revenue': '${:.2f}'}))
        report.add(frame)
        html = HTMLWriter().render(report.document)
        self.assertEqual(html.count('<table'), 2)
        self.assertIn('$12.00', html)

    @unittest.skipUnless(importlib.util.find_spec('altair'), 'altair is not installed')
    def test_altair_charts_have_unique_targets(self):
        import altair as alt

        chart = (
            alt.Chart(alt.Data(values=[{'x': 1, 'y': 2}]))
            .mark_point()
            .encode(x='x:Q', y='y:Q')
        )
        report = Report()
        report.add(chart)
        report.add(chart)
        html = HTMLWriter().render(report.document)
        self.assertEqual(html.count('class="report-artifact"'), 2)
        self.assertEqual(html.count('vegaEmbed('), 2)
        self.assertIn('reporttkt_chart_', html)

    @unittest.skipUnless(
        importlib.util.find_spec('altair') and importlib.util.find_spec('vl_convert'),
        'altair and vl-convert-python are not installed',
    )
    def test_altair_offline_mode_inlines_scripts(self):
        import altair as alt

        chart = alt.Chart(alt.Data(values=[{'x': 1}])).mark_bar().encode(x='x:Q')
        report = Report()
        report.add(chart)
        html = HTMLWriter(inline_altair=True).render(report.document)
        self.assertIn('vegaEmbed(', html)
        self.assertNotIn('<script type="text/javascript" src="https://', html)

    @unittest.skipUnless(
        importlib.util.find_spec('matplotlib'), 'matplotlib is not installed'
    )
    def test_matplotlib_embeds_png(self):
        from matplotlib.figure import Figure

        figure = Figure(figsize=(2, 1))
        figure.subplots().plot([1, 2], [3, 4])
        report = Report()
        report.add(figure, caption='Trend')
        html = HTMLWriter().render(report.document)
        self.assertIn('data:image/png;base64,iVBOR', html)
        self.assertIn('<figcaption>Trend</figcaption>', html)

    @unittest.skipUnless(importlib.util.find_spec('plotly'), 'plotly is not installed')
    def test_plotly_uses_cdn_fragment(self):
        import plotly.graph_objects as go

        report = Report()
        report.add(go.Figure(data=go.Bar(x=['Jan'], y=[12])), caption='Revenue')
        html = HTMLWriter().render(report.document)
        self.assertIn('<figcaption>Revenue</figcaption>', html)
        self.assertIn('cdn.plot.ly/plotly-', html)
        self.assertIn('Plotly.newPlot(', html)
        self.assertEqual(html.count('<!doctype html>'), 1)


if __name__ == '__main__':
    unittest.main()

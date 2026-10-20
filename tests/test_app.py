import os
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
import analytics
import education_visuals


class DashboardFlow(unittest.TestCase):
    def test_existing_session_reloads_visual_layout(self):
        original_figure = education_visuals.education_figure
        def stale_figure(*args, **kwargs):
            figure = original_figure(*args, **kwargs)
            figure.update_xaxes(side='top')
            return figure
        with patch.dict(os.environ, {"DASHBOARD_DEMO": "1"}), \
             patch.object(education_visuals, 'VISUAL_LAYOUT_VERSION', 1), \
             patch.object(education_visuals, 'education_figure', stale_figure):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
            self.assertFalse(app.exception)
            chart = json.loads(app.tabs[1].get('plotly_chart')[0].proto.spec)
            self.assertEqual(chart['layout']['xaxis']['side'], 'bottom')
            self.assertEqual(chart['layout']['xaxis2']['side'], 'bottom')

    def test_existing_session_reloads_old_analytics_schema(self):
        original_calculate = analytics.calculate
        def stale_calculate(*args, **kwargs):
            summary, institutions, people, quality = original_calculate(*args, **kwargs)
            return summary.drop(columns='academic_cutoff'), institutions, people, quality
        with patch.dict(os.environ, {"DASHBOARD_DEMO": "1"}), \
             patch.object(analytics, 'RESULT_SCHEMA_VERSION', 3), \
             patch.object(analytics, 'calculate', stale_calculate):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.tabs[1].get('plotly_chart')), 1)
            export = next(d.value for d in app.dataframe if 'Fecha de corte académico' in d.value.columns)
            self.assertTrue(export['Fecha de corte académico'].notna().all())

    def test_careers_and_cutoff_recalculate_without_errors(self):
        with patch.dict(os.environ, {"DASHBOARD_DEMO": "1"}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.sidebar.multiselect),0)
            self.assertEqual(len(app.sidebar.selectbox),0)
            self.assertEqual(len(app.multiselect),1)
            self.assertEqual([tab.label for tab in app.tabs], ["Empleo y salarios", "Educación e instituciones", "Metodología y calidad"])
            self.assertEqual(len(app.tabs[1].get('plotly_chart')),1)
            private = next(d.value for d in app.dataframe if 'Sigla' in d.value.columns)
            self.assertEqual(len(private),18)
            initial = int(app.metric[0].value.replace('.', ''))
            app.multiselect[0].set_value(["Economía", "Finanzas"]).run()
            self.assertFalse(app.exception)
            combined = int(app.metric[0].value.replace('.', ''))
            recent_2026 = app.metric[2].value
            self.assertGreater(combined, initial)
            app.selectbox[0].set_value(2023).run()
            self.assertFalse(app.exception)
            earlier = int(app.metric[0].value.replace('.', ''))
            self.assertLess(earlier, combined)
            self.assertEqual(app.metric[2].value,recent_2026)
            app.multiselect[0].set_value([]).run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Selecciona al menos' in x.value for x in app.info))


if __name__ == '__main__':
    unittest.main()

import unittest

from simlab.queue import QueueConfig, recommended_servers, size_queue
from simlab.report import histogram, queue_report, risk_report
from simlab.risk import RiskConfig, Task, finish_date, simulate_risk


class ReportTests(unittest.TestCase):
    def test_queue_title_key_numbers_and_svg(self):
        config = QueueConfig(0.7, 1, customers=100, max_servers=3)
        results = size_queue(config)
        report = queue_report(config, results)
        self.assertIn("Coffee shop queue / staffing decision", report)
        self.assertIn(f"{results[1].mean_wait_minutes:.3f} min", report)
        self.assertIn(f"<dd>{recommended_servers(config, results)}</dd>", report)
        self.assertIn("<svg", report)

    def test_risk_title_key_numbers_dates_and_svg(self):
        config = RiskConfig((Task("A", 1, 2, 3),), trials=100)
        result = simulate_risk(config)
        report = risk_report(config, result)
        self.assertIn("Project risk / finish-date forecast", report)
        for value in (result.p50, result.p80, result.p95):
            self.assertIn(f"{value:.3f} days", report)
            self.assertIn(finish_date(config, value), report)
        self.assertIn("<svg", report)

    def test_escapes_task_names(self):
        config = RiskConfig((Task('<script>alert("x")</script>', 1, 2, 3),), trials=10)
        report = risk_report(config, simulate_risk(config))
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)

    def test_histogram_constant_data_and_accessible_label(self):
        report = histogram((5, 5, 5), 'Duration "days"')
        self.assertIn('role="img"', report)
        self.assertIn("&quot;days&quot;", report)
        self.assertIn("3 samples", report)
        self.assertNotIn("nan", report)

    def test_unmet_target_explained(self):
        config = QueueConfig(0.7, 1, customers=10, target_wait_minutes=0)
        self.assertIn("None in range", queue_report(config, size_queue(config)))

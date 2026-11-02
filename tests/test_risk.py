import math
import unittest
from dataclasses import replace

from simlab.risk import RiskConfig, Task, finish_date, simulate_risk


class RiskTests(unittest.TestCase):
    def setUp(self):
        self.config = RiskConfig((Task("Design", 2, 4, 10),), trials=1000)

    def test_reproducible(self):
        self.assertEqual(simulate_risk(self.config), simulate_risk(self.config))

    def test_order_and_bounds(self):
        result = simulate_risk(self.config)
        self.assertLessEqual(result.p50, result.p80)
        self.assertLessEqual(result.p80, result.p95)
        self.assertGreaterEqual(min(result.durations), 2)
        self.assertLessEqual(max(result.durations), 10)

    def test_one_task_matches_triangular_quantiles(self):
        result = simulate_risk(replace(self.config, trials=200_000))
        # For a=2, m=4, b=10, F(m)=1/4; all three quantiles use the upper branch.
        for probability, actual in ((0.5, result.p50), (0.8, result.p80), (0.95, result.p95)):
            expected = 10 - math.sqrt((1 - probability) * (10 - 2) * (10 - 4))
            print(f"Triangular P{probability * 100:g}: simulated={actual:.9f}; "
                  f"formula={expected:.9f}")
            self.assertAlmostEqual(actual, expected, delta=0.025)

    def test_hand_computed_constant_project(self):
        config = RiskConfig((Task("A", 2, 2, 2), Task("B", 3, 3, 3)), trials=10)
        result = simulate_risk(config)
        self.assertEqual((result.p50, result.p80, result.p95), (5, 5, 5))
        self.assertEqual(result.durations, (5,) * 10)

    def test_calendar_finish_rounds_up_and_crosses_month(self):
        config = replace(self.config, start_date="2026-01-30")
        self.assertEqual(finish_date(config, 2.1), "2026-02-02")
        self.assertEqual(finish_date(config, 0), "2026-01-30")

    def test_rejects_bad_tasks(self):
        for args in (("", 1, 2, 3), ("A", -1, 2, 3), ("A", 3, 2, 4),
                     ("A", 1, 4, 3), ("A", 1, 2, float("inf"))):
            with self.subTest(args=args), self.assertRaises(ValueError):
                Task(*args)

    def test_rejects_bad_configs(self):
        for changes in ({"tasks": ()}, {"trials": 0}, {"seed": -1}, {"trials": True},
                        {"start_date": "2026-02-30"}, {"start_date": "20260101"},
                        {"tasks": (Task("A", 1, 2, 3), Task("A", 1, 2, 3))}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.config, **changes)

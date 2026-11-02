import math
import unittest
from dataclasses import replace

from simlab.queue import QueueConfig, recommended_servers, simulate_queue, size_queue


class QueueTests(unittest.TestCase):
    def test_reproducible(self):
        config = QueueConfig(0.7, 1, customers=100)
        self.assertEqual(simulate_queue(config), simulate_queue(config))

    def test_mm1_matches_formula(self):
        config = QueueConfig(0.7, 1, servers=1, customers=1_000_000, warmup=20_000)
        expected = 0.7 / (1 - 0.7)
        actual = simulate_queue(config).mean_wait_minutes
        print(f"M/M/1: simulated={actual:.9f}; formula={expected:.9f}; "
              f"relative_error={abs(actual / expected - 1):.6%}")
        self.assertLess(abs(actual / expected - 1), 0.05)

    def test_mmc_matches_erlang_c(self):
        arrival, service, servers = 2.1, 1, 3
        offered = arrival / service
        rho = offered / servers
        tail = offered**servers / (math.factorial(servers) * (1 - rho))
        p_wait = tail / (sum(offered**k / math.factorial(k) for k in range(servers)) + tail)
        expected = p_wait / (servers * service - arrival)
        actual = simulate_queue(QueueConfig(
            arrival, service, servers=servers, customers=1_000_000, warmup=20_000
        )).mean_wait_minutes
        print(f"M/M/3: simulated={actual:.9f}; formula={expected:.9f}; "
              f"relative_error={abs(actual / expected - 1):.6%}")
        self.assertLess(abs(actual / expected - 1), 0.05)

    def test_sample_count_and_nonnegative_waits(self):
        result = simulate_queue(QueueConfig(0.7, 1, customers=80, warmup=50))
        self.assertEqual(len(result.waits), 80)
        self.assertGreaterEqual(min(result.waits), 0)
        self.assertGreater(result.mean_system_minutes, result.mean_wait_minutes)

    def test_staffing_skips_unstable_counts_and_meets_target(self):
        config = QueueConfig(1.4, 1, customers=10_000, target_wait_minutes=0.5, max_servers=4)
        results = size_queue(config)
        self.assertEqual([r.servers for r in results], [2, 3, 4])
        self.assertEqual(recommended_servers(config, results), 3)
        self.assertEqual(results[0], simulate_queue(config))

    def test_unmet_and_strict_zero_target(self):
        config = QueueConfig(0.7, 1, customers=20, target_wait_minutes=0)
        self.assertIsNone(recommended_servers(config, size_queue(config)))

    def test_rejects_invalid_configs(self):
        config = QueueConfig(0.7, 1)
        for changes in (
            {"arrival_rate": 0}, {"service_rate": -1}, {"arrival_rate": float("nan")},
            {"service_rate": float("inf")}, {"customers": 0}, {"warmup": -1},
            {"servers": 1.5}, {"seed": True}, {"max_servers": 1},
            {"target_wait_minutes": -1},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(config, **changes)

    def test_rejects_unstable_queue(self):
        with self.assertRaisesRegex(ValueError, "stable"):
            simulate_queue(QueueConfig(1, 1, servers=1))

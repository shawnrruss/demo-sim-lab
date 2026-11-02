import contextlib
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from simlab.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config.json"
        self.out = self.root / "nested" / "output"

    def invoke(self, model, config):
        self.config.write_text(json.dumps(config), encoding="utf-8")
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main([model, "--config", str(self.config), "--out", str(self.out)])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_queue_writes_report_and_csv(self):
        code, stdout, stderr = self.invoke(
            "queue", {"arrival_rate": 0.7, "service_rate": 1, "customers": 100}
        )
        self.assertEqual((code, stderr), (0, ""))
        self.assertIn("recommended_servers=", stdout)
        self.assertIn("<svg", (self.out / "queue.html").read_text(encoding="utf-8"))
        with (self.out / "queue.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]["servers"], "1")

    def test_risk_writes_report_and_csv(self):
        code, stdout, stderr = self.invoke(
            "risk", {"tasks": [{"name": "A", "low": 2, "mode": 2, "high": 2}], "trials": 10}
        )
        self.assertEqual((code, stderr), (0, ""))
        self.assertIn("P80=2.000 days", stdout)
        self.assertTrue((self.out / "risk.html").is_file())
        with (self.out / "risk.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([row["percentile"] for row in rows], ["50", "80", "95"])
        self.assertEqual(rows[1]["finish_date"], "2026-01-03")

    def test_bad_configs_exit_two_with_message(self):
        for model, config in (
            ("queue", {"arrival_rate": -1, "service_rate": 1}),
            ("queue", {"arrival_rate": 4, "service_rate": 1}),
            ("queue", {"arrival_rate": 1, "service_rate": 2, "unknown": 1}),
            ("queue", []), ("risk", {"tasks": []}), ("risk", {"tasks": [1]}),
            ("risk", {"tasks": [{"name": "A", "low": 2, "mode": 1, "high": 3}]}),
        ):
            with self.subTest(model=model, config=config):
                code, _, stderr = self.invoke(model, config)
                self.assertEqual(code, 2)
                self.assertIn("error:", stderr)
                self.assertFalse(self.out.exists())

    def test_invalid_json_and_missing_file(self):
        self.config.write_text("{", encoding="utf-8")
        for path in (self.config, self.root / "missing.json"):
            with self.subTest(path=path), contextlib.redirect_stderr(io.StringIO()) as stderr:
                code = main(["queue", "--config", str(path), "--out", str(self.out)])
                self.assertEqual(code, 2)
                self.assertIn("error:", stderr.getvalue())

    def test_module_entrypoint_and_bad_config_process_exit(self):
        self.config.write_text('{"arrival_rate": -1, "service_rate": 1}', encoding="utf-8")
        process = subprocess.run(
            [sys.executable, "-m", "simlab.cli", "queue", "--config", str(self.config),
             "--out", str(self.out)], capture_output=True, text=True, check=False,
        )
        self.assertEqual(process.returncode, 2)
        self.assertIn("error:", process.stderr)
        self.assertNotIn("Traceback", process.stderr)

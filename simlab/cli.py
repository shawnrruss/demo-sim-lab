"""Run with python -m simlab.cli {queue,risk} --config FILE --out DIR."""

import argparse
import csv
import json
import sys
from pathlib import Path

from simlab.queue import QueueConfig, recommended_servers, size_queue
from simlab.report import queue_report, risk_report
from simlab.risk import RiskConfig, Task, finish_date, simulate_risk


def write_csv(path: Path, fields: tuple[str, ...], rows: list[tuple]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="model", required=True)
    for name in ("queue", "risk"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.config.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("config must be a JSON object")
        if args.model == "queue":
            config = QueueConfig(**data)
            results = size_queue(config)
            if not any(result.servers == config.servers for result in results):
                raise ValueError("configured queue must be stable")
            report = queue_report(config, results)
            fields = ("servers", "mean_wait_minutes", "mean_system_minutes", "utilization")
            rows = [
                (r.servers, r.mean_wait_minutes, r.mean_system_minutes, r.utilization)
                for r in results
            ]
            selected = next(r for r in results if r.servers == config.servers)
            summary = (
                f"mean_wait_minutes={selected.mean_wait_minutes:.3f}; "
                f"recommended_servers={recommended_servers(config, results)}"
            )
        else:
            if not isinstance(data.get("tasks"), list) or not all(
                isinstance(task, dict) for task in data["tasks"]
            ):
                raise ValueError("tasks must be a nonempty array of task objects")
            config = RiskConfig(**{**data, "tasks": tuple(Task(**task) for task in data["tasks"])})
            result = simulate_risk(config)
            report = risk_report(config, result)
            fields = ("percentile", "duration_days", "finish_date")
            rows = [
                (percent, value, finish_date(config, value))
                for percent, value in ((50, result.p50), (80, result.p80), (95, result.p95))
            ]
            summary = "; ".join(
                f"P{percent}={value:.3f} days ({day})" for percent, value, day in rows
            )
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / f"{args.model}.html").write_text(report, encoding="utf-8", newline="\n")
        write_csv(args.out / f"{args.model}.csv", fields, rows)
    except (OSError, ValueError, TypeError, OverflowError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(summary)
    print(f"Wrote {args.out / (args.model + '.html')} and {args.out / (args.model + '.csv')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

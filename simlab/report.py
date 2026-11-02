"""Escaped, self-contained HTML with inline SVG histograms."""

from html import escape

from simlab.queue import QueueConfig, QueueResult, recommended_servers
from simlab.risk import RiskConfig, RiskResult, finish_date


def histogram(values: tuple[float, ...], label: str, bins: int = 20) -> str:
    lower, upper = min(values), max(values)
    width = (upper - lower) / bins if upper > lower else 1.0
    counts = [0] * bins
    for value in values:
        counts[min(int((value - lower) / width), bins - 1)] += 1
    bars = []
    for index, count in enumerate(counts):
        height = 160 * count / max(counts)
        bars.append(
            f'<rect x="{55 + index * 25}" y="{190 - height:.2f}" '
            f'width="23" height="{height:.2f}"><title>{count} samples</title></rect>'
        )
    return (
        f'<svg viewBox="0 0 620 240" role="img" aria-label="{escape(label, quote=True)}">'
        f'<title>{escape(label)}</title><g fill="#087f8c">{"".join(bars)}</g>'
        '<path d="M55 25 V190 H555" fill="none" stroke="#536171"/>'
        f'<text x="55" y="212">{lower:.2f}</text>'
        f'<text x="555" y="212" text-anchor="end">{upper:.2f}</text>'
        f'<text x="305" y="235" text-anchor="middle">{escape(label)}</text>'
        '<text x="12" y="18">Count</text></svg>'
    )


def page(title: str, cards: dict[str, str], chart: str, details: str, note: str) -> str:
    metrics = "".join(
        f'<div class="metric"><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>'
        for label, value in cards.items()
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #edf3f5; color: #172b3a;
        font: 16px/1.5 system-ui, sans-serif; }}
main {{ max-width: 940px; margin: 24px auto; padding: 30px; background: white;
        border-top: 6px solid #087f8c; border-radius: 12px; }}
h1 {{ margin: 0; font-size: 30px; }} h2 {{ font-size: 19px; margin-bottom: 8px; }}
.eyebrow {{ color: #087f8c; font-weight: 700; letter-spacing: .12em; }}
dl {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 22px 0; }}
.metric {{ flex: 1; min-width: 170px; padding: 14px; background: #edf7f7; }}
dt {{ font-size: 14px; }} dd {{ margin: 4px 0 0; font-size: 24px; font-weight: 700; }}
svg {{ display: block; width: 100%; max-height: 280px; }}
svg text {{ font: 13px system-ui, sans-serif; fill: #536171; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }}
th, td {{ text-align: left; padding: 7px; border-bottom: 1px solid #dce5e9; }}
footer {{ font-size: 13px; color: #536171; margin-top: 20px; }}
@media print {{ body {{ background: white; }} main {{ margin: 0; padding: 16px; }} }}
</style></head><body><main>
<div class="eyebrow">SIMLAB / SIMULATED DATA ONLY</div>
<h1>{escape(title)}</h1><p>{escape(note)}</p><dl>{metrics}</dl>
{chart}{details}
<footer>Simulated data only. Seeded scenario estimates, not operational guarantees.
No external assets, scripts, or tracking.</footer>
</main></body></html>
'''


def queue_report(config: QueueConfig, results: tuple[QueueResult, ...]) -> str:
    selected = next(result for result in results if result.servers == config.servers)
    recommended = recommended_servers(config, results)
    cards = {
        f"Mean wait / {config.servers} servers": f"{selected.mean_wait_minutes:.3f} min",
        f"Servers for wait < {config.target_wait_minutes:g} min": (
            str(recommended) if recommended is not None else "None in range"
        ),
        "Offered utilization": f"{selected.utilization:.1%}",
    }
    rows = "".join(
        f"<tr><td>{r.servers}</td><td>{r.mean_wait_minutes:.3f}</td>"
        f"<td>{r.mean_system_minutes:.3f}</td><td>{r.utilization:.1%}</td></tr>"
        for r in results
    )
    return page(
        "Coffee shop queue / staffing decision", cards,
        histogram(selected.waits, "Wait in minutes"),
        '<h2>Stable staffing scenarios</h2><table><thead><tr><th>Servers</th>'
        '<th>Mean wait (min)</th><th>Mean total time (min)</th><th>Utilization</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>',
        f"FCFS; exponential arrivals ({config.arrival_rate:g}/min) and service "
        f"({config.service_rate:g}/min/server). {config.customers:,} measured arrivals after "
        f"{config.warmup:,} warm-up arrivals per scenario; seed {config.seed}. "
        f"Search: 1–{config.max_servers} servers; unstable counts excluded. "
        "Recommendation uses a strict mean-wait threshold and one run per count.",
    )


def risk_report(config: RiskConfig, result: RiskResult) -> str:
    cards = {
        f"P{percent} / calendar finish": f"{value:.3f} days / {finish_date(config, value)}"
        for percent, value in ((50, result.p50), (80, result.p80), (95, result.p95))
    }
    rows = "".join(
        f"<tr><td>{escape(task.name)}</td><td>{task.low:g}</td>"
        f"<td>{task.mode:g}</td><td>{task.high:g}</td></tr>"
        for task in config.tasks
    )
    return page(
        "Project risk / finish-date forecast", cards,
        histogram(result.durations, "Project duration in calendar days"),
        '<h2>Triangular task estimates (days)</h2><table><thead><tr><th>Task</th>'
        '<th>Low</th><th>Most likely</th><th>High</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>',
        f"{config.trials:,} trials; seed {config.seed}; start {config.start_date}. "
        "Independent sequential tasks, summed durations. Finish dates round up to the next "
        "whole calendar day, including weekends. P80 means 80% of simulated projects finish "
        "within that duration; no resource constraints or task overlap are modeled.",
    )

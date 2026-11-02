"""Sequential project tasks with independent triangular durations, in days."""

from dataclasses import dataclass
from datetime import date, timedelta
from math import ceil

from simlab import integer, number, seeded_rng


@dataclass(frozen=True)
class Task:
    name: str
    low: float
    mode: float
    high: float

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("task name must be a nonempty string")
        for name in ("low", "mode", "high"):
            number(name, getattr(self, name))
        if not self.low <= self.mode <= self.high:
            raise ValueError("task durations must satisfy low <= mode <= high")


@dataclass(frozen=True)
class RiskConfig:
    tasks: tuple[Task, ...]
    trials: int = 50_000
    seed: int = 42
    start_date: str = "2026-01-01"

    def __post_init__(self) -> None:
        if not self.tasks or any(not isinstance(task, Task) for task in self.tasks):
            raise ValueError("tasks must be a nonempty sequence of Task objects")
        if len({task.name for task in self.tasks}) != len(self.tasks):
            raise ValueError("task names must be unique")
        integer("trials", self.trials, 1)
        integer("seed", self.seed)
        if not isinstance(self.start_date, str):
            raise ValueError("start_date must be an ISO date: YYYY-MM-DD")
        try:
            parsed = date.fromisoformat(self.start_date)
            if parsed.isoformat() != self.start_date:
                raise ValueError
        except ValueError as error:
            raise ValueError("start_date must be an ISO date: YYYY-MM-DD") from error


@dataclass(frozen=True)
class RiskResult:
    p50: float
    p80: float
    p95: float
    durations: tuple[float, ...]


def quantile(sorted_values: list[float], probability: float) -> float:
    """Linear interpolation between adjacent order statistics."""
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (position - lower)


def simulate_risk(config: RiskConfig) -> RiskResult:
    rng = seeded_rng(config.seed)
    durations = tuple(
        sum(rng.triangular(task.low, task.high, task.mode) for task in config.tasks)
        for _ in range(config.trials)
    )
    ordered = sorted(durations)
    return RiskResult(*(quantile(ordered, p) for p in (0.5, 0.8, 0.95)), durations)


def finish_date(config: RiskConfig, duration: float) -> str:
    """Round up to a whole calendar day; weekends are included."""
    return (date.fromisoformat(config.start_date) + timedelta(days=ceil(duration))).isoformat()

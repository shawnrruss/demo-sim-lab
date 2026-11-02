"""FCFS M/M/c queue: exponential interarrival and service times, minutes."""

from dataclasses import dataclass, replace
from heapq import heapreplace
from statistics import fmean

from simlab import integer, number, seeded_rng


@dataclass(frozen=True)
class QueueConfig:
    arrival_rate: float
    service_rate: float
    servers: int = 2
    customers: int = 50_000
    warmup: int = 5_000
    seed: int = 42
    target_wait_minutes: float = 2.0
    max_servers: int = 6

    def __post_init__(self) -> None:
        number("arrival_rate", self.arrival_rate, positive=True)
        number("service_rate", self.service_rate, positive=True)
        integer("servers", self.servers, 1)
        integer("customers", self.customers, 1)
        integer("warmup", self.warmup)
        integer("seed", self.seed)
        integer("max_servers", self.max_servers, self.servers)
        number("target_wait_minutes", self.target_wait_minutes)


@dataclass(frozen=True)
class QueueResult:
    servers: int
    mean_wait_minutes: float
    mean_system_minutes: float
    utilization: float
    waits: tuple[float, ...]


def simulate_queue(config: QueueConfig) -> QueueResult:
    """Discard warmup arrivals, then measure exactly customers arrivals.

    The heap stores each server's next free time. Its minimum gives the next
    service start; heap replacement advances that server's departure event.
    Unstable configurations are rejected because no steady-state mean exists.
    """
    utilization = config.arrival_rate / (config.servers * config.service_rate)
    if utilization >= 1:
        raise ValueError("queue must be stable: arrival_rate < servers * service_rate")
    rng = seeded_rng(config.seed)
    available = [0.0] * config.servers
    arrival = 0.0
    waits = []
    system_times = []
    for index in range(config.warmup + config.customers):
        arrival += rng.expovariate(config.arrival_rate)
        start = max(arrival, available[0])
        service = rng.expovariate(config.service_rate)
        heapreplace(available, start + service)
        if index >= config.warmup:
            waits.append(start - arrival)
            system_times.append(start - arrival + service)
    return QueueResult(
        config.servers, fmean(waits), fmean(system_times), utilization, tuple(waits)
    )


def size_queue(config: QueueConfig) -> tuple[QueueResult, ...]:
    """Compare every stable server count up to max_servers using the same seed."""
    return tuple(
        simulate_queue(replace(config, servers=count))
        for count in range(1, config.max_servers + 1)
        if config.arrival_rate < count * config.service_rate
    )


def recommended_servers(config: QueueConfig, results: tuple[QueueResult, ...]) -> int | None:
    return next(
        (r.servers for r in results if r.mean_wait_minutes < config.target_wait_minutes), None
    )

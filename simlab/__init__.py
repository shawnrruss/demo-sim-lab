"""Generic simulations using simulated data only; no runtime dependencies."""

import math
import random


def integer(name: str, value: int, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def number(name: str, value: float, *, positive: bool = False) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or (value <= 0 if positive else value < 0)
    ):
        bound = "> 0" if positive else ">= 0"
        raise ValueError(f"{name} must be a finite number {bound}")


def seeded_rng(seed: int) -> random.Random:
    """Create a private RNG without changing the process-wide random state."""
    integer("seed", seed)
    return random.Random(seed)

"""Seeded half-line workloads and CSV input/output; every position is in [0,L]."""

import csv
import random
from pathlib import Path

from halfline_trp import Config, Request


PATTERNS = ("uniform", "early", "bursty", "near_origin", "near_endpoint", "endpoints", "hotspots", "half_grid")


def generate_requests(n: int, length: float, arrival_horizon: int, seed: int = 7,
                      pattern: str = "uniform") -> list[Request]:
    """Generate exactly n requests with integer releases in [0,arrival_horizon].

    length is the distance from zero to the physical endpoint, with no halving.
    A local Random instance makes repeated seeds reproducible without changing
    the caller's global RNG. These distributions are experiments, not proven
    worst-case adversaries. Repeated coordinates and times remain distinct IDs.
    """
    Config(length=length)
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise ValueError("n must be a nonnegative integer.")
    if (not isinstance(arrival_horizon, int) or isinstance(arrival_horizon, bool)
            or arrival_horizon < 0):
        raise ValueError("arrival_horizon must be a nonnegative integer.")
    if pattern not in PATTERNS:
        raise ValueError(f"Unknown pattern {pattern!r}; choose from {PATTERNS}.")
    rng = random.Random(seed)
    bursts = [0, arrival_horizon // 3, 2 * arrival_horizon // 3, arrival_horizon]
    requests = []
    for i in range(n):
        release = rng.randint(0, arrival_horizon)
        position = rng.uniform(0, length)
        if pattern == "early":
            release = 0
        elif pattern == "bursty":
            release = rng.choice(bursts)
        elif pattern == "near_origin":
            position = rng.uniform(0, 0.05 * length)
        elif pattern == "near_endpoint":
            position = rng.uniform(0.95 * length, length)
        elif pattern == "endpoints":
            position = rng.choice([0.0, length])
        elif pattern == "hotspots":
            center = rng.choice([0.1, 0.5, 0.9]) * length
            position = min(length, max(0.0, rng.gauss(center, 0.015 * length)))
        elif pattern == "half_grid":
            position = 0.5 * rng.randint(0, int(length / 0.5))
        requests.append(Request(i, release, position))
    return requests


def read_requests(path: str | Path) -> list[Request]:
    """Read id,release_time,position; input order need not be chronological."""
    with open(path, newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not {"id", "release_time", "position"}.issubset(reader.fieldnames or []):
            raise ValueError("CSV requires id,release_time,position columns.")
        requests = []
        for line, row in enumerate(reader, start=2):
            try:
                requests.append(Request(int(row["id"]), float(row["release_time"]), float(row["position"])))
            except (ValueError, TypeError) as error:
                raise ValueError(f"Invalid CSV row {line}: {error}") from error
    return requests


def write_requests(path: str | Path, requests: list[Request]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["id", "release_time", "position"])
        writer.writerows((r.id, r.release, r.position) for r in requests)

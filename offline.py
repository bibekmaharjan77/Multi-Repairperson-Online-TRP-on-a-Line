"""Exact small-instance offline benchmark for sum of completion times.

All m servers start at zero at time zero, may pre-position before releases,
and may wait. Requests and feasible routes stay inside [0, length]. There is
no requirement to return to zero. The optimization uses no online waypoints.

Exactness is combinatorial; coordinates and costs use Python float arithmetic.
The number of nondominated route labels can be exponential. The default input
limit is 10 requests. No heuristic is silently substituted for OPT.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import inf
from typing import Sequence

from halfline_trp import Config, Request, validate_requests


@dataclass(frozen=True)
class Label:
    finish: float
    cost: float
    route: tuple[int, ...]  # Indices into the input sequence


@dataclass(frozen=True)
class OfflineResult:
    total_completion_time: float
    routes: list[list[int]]  # Request IDs, one route per server (empty allowed)
    completion_times: dict[int, float]
    retained_labels: int
    method: str


def _insert(frontier: list[Label], candidate: Label) -> None:
    """Keep time/cost Pareto labels for one (served subset, last request).

    A cheaper partial route can finish later; keeping only its cost would lose
    an optimal continuation. A label dominates another only if it finishes no
    later AND costs no more. We do not use epsilon in these comparisons.
    """
    if any(old.finish <= candidate.finish and old.cost <= candidate.cost for old in frontier):
        return
    frontier[:] = [old for old in frontier
                   if not (candidate.finish <= old.finish and candidate.cost <= old.cost)]
    frontier.append(candidate)


def exact_offline(requests: Sequence[Request], config: Config, *, max_requests: int = 10,
                  max_labels: int = 1_000_000) -> OfflineResult:
    """Optimize every single-server subset route, then partition among m servers.

    For a route ending at (x, time), append request (y, release) at
        next_time = max(release, time + abs(y - x)).
    The initial transition uses time=0 and x=0, allowing offline anticipation.
    For every subset, minimize over its final location and nondominated labels.
    Then find the minimum sum over partitions into at most m such subsets.

    Automatic service on passing other requests does not invalidate this model:
    every true optimal schedule induces service orders represented by these
    transitions, and every enumerated route is feasible with service no later
    than its designated completion times. See README.md for the argument.
    """
    validate_requests(requests, config)
    m = config.repairpersons
    n = len(requests)
    if n == 0:
        return OfflineResult(0.0, [[] for _ in range(m)], {}, 0, "empty_instance")
    if m >= n:
        # Each request can have a dedicated server: the independent lower bounds
        # are simultaneously achievable, even for a large input.
        times = {r.id: r.lower_bound for r in requests}
        return OfflineResult(sum(times.values()), [[r.id] for r in requests]
                             + [[] for _ in range(m - n)], times, n, "dedicated_servers")
    if n > max_requests:
        raise ValueError(f"Exact OPT limited to {max_requests} requests; received {n}.")

    size = 1 << n
    labels: list[dict[int, list[Label]]] = [{} for _ in range(size)]
    best: list[Label | None] = [None] * size
    best[0] = Label(0, 0, ())
    for i, request in enumerate(requests):
        finish = request.lower_bound
        labels[1 << i][i] = [Label(finish, finish, (i,))]
    retained = n
    for mask in range(1, size):
        all_labels = [label for frontier in labels[mask].values() for label in frontier]
        best[mask] = min(all_labels, key=lambda label: (label.cost, label.finish, label.route))
        remaining = (size - 1) ^ mask
        for last, frontier in labels[mask].items():
            for label in frontier:
                bits = remaining
                while bits:
                    bit = bits & -bits
                    bits ^= bit
                    next_index = bit.bit_length() - 1
                    request = requests[next_index]
                    finish = max(request.release, label.finish
                                 + abs(request.position - requests[last].position))
                    candidate = Label(finish, label.cost + finish, label.route + (next_index,))
                    target = labels[mask | bit].setdefault(next_index, [])
                    old_count = len(target)
                    _insert(target, candidate)
                    retained += len(target) - old_count
                    if retained > max_labels:
                        raise ValueError("Exact OPT label budget exceeded; reduce request count.")

    @lru_cache(maxsize=None)
    def partition(mask: int, available: int) -> tuple[float, tuple[int, ...]]:
        if mask == 0:
            return 0.0, ()
        if available == 1:
            assert best[mask] is not None
            return best[mask].cost, (mask,)
        # Servers are interchangeable. Force the next subset to contain the
        # lowest-index unassigned request, removing redundant server permutations.
        anchor = mask & -mask
        subset = mask
        optimum, chosen = inf, ()
        while subset:
            if subset & anchor:
                remainder, tail = partition(mask ^ subset, available - 1)
                assert best[subset] is not None
                value = best[subset].cost + remainder
                if value < optimum:
                    optimum, chosen = value, (subset,) + tail
            subset = (subset - 1) & mask
        return optimum, chosen

    cost, subsets = partition(size - 1, min(m, n))
    routes, completion_times = [], {}
    for subset in subsets:
        label = best[subset]
        assert label is not None
        route, now, position = [], 0.0, 0.0
        for i in label.route:
            request = requests[i]
            now = max(request.release, now + abs(position - request.position))
            completion_times[request.id] = now
            route.append(request.id)
            position = request.position
        routes.append(route)
    routes.extend([] for _ in range(m - len(routes)))
    return OfflineResult(cost, routes, completion_times, retained, "pareto_routes_and_subset_partition")

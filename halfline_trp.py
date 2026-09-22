"""Multi-repairperson online TRP on the physical interval [0, length].

All m repairpersons start at 0 at time 0 and patrol continuously. For m=1,
use one half of Algorithm 1 in the supplied manuscript. For m>=2, use
Algorithm 2's half-line schedule with alpha=2/(5*m-3), beta=5/(5*m-3).

The geometric timetable is projected onto [0, length]: a repairperson waits
at the endpoint whenever its virtual position is farther out. No left/right
allocation, negative coordinates, or request-dependent pausing occurs here.

Only the Python standard library is needed. See README.md and THEORY.md.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import asdict, dataclass
from math import fsum, isfinite, sqrt, ulp
from typing import Iterator, Sequence


def _time_tolerance(a: float, b: float) -> float:
    """Eight floating-point units for nearly coincident computed timestamps."""
    return 8 * max(ulp(a), ulp(b))


@dataclass(frozen=True)
class Request:
    """A unique request at x>=0, released at t>=0, with zero service duration."""

    id: int
    release: float
    position: float

    def __post_init__(self) -> None:
        if not isinstance(self.id, int) or isinstance(self.id, bool):
            raise ValueError("Request IDs must be integers.")
        if not isfinite(self.release) or self.release < 0:
            raise ValueError("Release times must be finite and nonnegative.")
        if not isfinite(self.position) or self.position < 0:
            raise ValueError("Half-line request positions must be finite and nonnegative.")

    @property
    def lower_bound(self) -> float:
        """Individual optimum max(t,x); generally only a joint-OPT lower bound."""
        return max(self.release, self.position)


@dataclass(frozen=True)
class Config:
    """Confirmed model: m servers on [0,length], continuously patrolling at speed 1.

    'repairpersons' is the actual count simulated on this half-line, never a
    full-line count to be divided by two. Thus m=1 corresponds to paper k=2,
    m=2 to paper k=4, m=3 to paper k=6, under equal mirrored allocation.
    """

    length: float = 100.0
    repairpersons: int = 3

    def __post_init__(self) -> None:
        if not isfinite(self.length) or self.length <= 0:
            raise ValueError("length must be finite and strictly positive.")
        if (not isinstance(self.repairpersons, int) or isinstance(self.repairpersons, bool)
                or self.repairpersons < 1):
            raise ValueError("repairpersons must be an integer >= 1 on this half-line.")


@dataclass(frozen=True)
class Server:
    """A one-based local rank: S1 is innermost, Sm is outermost when m>=2."""

    id: int
    count: int

    @property
    def name(self) -> str:
        return f"S{self.id}"

    @property
    def role(self) -> str:
        if self.count == 1:
            return "single_round_trip"
        if self.id == 1:
            return "inner_round_trip"
        return "outer_partial_trip" if self.id == self.count else "middle_partial_trip"


@dataclass(frozen=True)
class Leg:
    """Linear motion or endpoint waiting on [t0,t1]; x0,x1 are nonnegative."""

    t0: float
    t1: float
    x0: float
    x1: float
    trip: int
    phase: str

    def position_at(self, time: float) -> float:
        if time <= self.t0:
            return self.x0
        if time >= self.t1:
            return self.x1
        if self.x0 == self.x1:
            return self.x0
        fraction = min(1.0, max(0.0, (time - self.t0) / (self.t1 - self.t0)))
        return self.x0 + fraction * (self.x1 - self.x0)

    def crossing(self, position: float, release: float) -> float | None:
        """First visit within this leg at/after release, including exact turns.

        Movement is evaluated analytically, never by sampling integer ticks.
        Time tolerance only reconciles floating-point representations of the
        same event. Returned completion times are never before release.
        """
        if self.x0 == self.x1:
            if position == self.x0 and release <= self.t1:
                return max(release, self.t0)
            return None
        if not min(self.x0, self.x1) <= position <= max(self.x0, self.x1):
            return None
        fraction = (position - self.x0) / (self.x1 - self.x0)
        visit = self.t0 + fraction * (self.t1 - self.t0)
        if visit < release and release - visit > _time_tolerance(visit, release):
            return None
        return max(visit, release, position)


@dataclass(frozen=True)
class Completion:
    request: Request
    time: float
    server: int


@dataclass
class Simulation:
    config: Config
    servers: list[Server]
    completions: list[Completion]
    trajectories: dict[int, list[Leg]]
    distance_by_server: dict[int, float]
    evaluated_horizon: float
    computed_legs: int

    def metrics(self) -> dict:
        n = len(self.completions)
        total = fsum(c.time for c in self.completions)
        lower_bound = fsum(c.request.lower_bound for c in self.completions)
        flows = [c.time - c.request.release for c in self.completions]
        ratios = [c.time / c.request.lower_bound for c in self.completions
                  if c.request.lower_bound > 0]
        maximum_ratio = max(ratios, default=None)
        claimed = claimed_halfline_bound(self.config.repairpersons)
        integer_releases = all(float(c.request.release).is_integer() for c in self.completions)
        return {
            "domain": "[0, length]", "length": self.config.length,
            "repairpersons": self.config.repairpersons,
            "corresponding_even_full_line_k": 2 * self.config.repairpersons,
            "requests": n, "total_completion_time": total,
            "mean_completion_time": total / n if n else 0.0,
            "total_flow_time": fsum(flows),
            "mean_flow_time": fsum(flows) / n if n else 0.0,
            "max_flow_time": max(flows, default=0.0),
            "makespan": max((c.time for c in self.completions), default=0.0),
            "total_distance_until_last_completion": fsum(self.distance_by_server.values()),
            "sum_individual_lower_bounds": lower_bound,
            "online_over_lower_bound": total / lower_bound if lower_bound else None,
            "max_request_over_lower_bound": maximum_ratio,
            "mean_request_over_lower_bound": fsum(ratios) / len(ratios) if ratios else None,
            "zero_lower_bound_requests": n - len(ratios),
            "paper_claimed_halfline_bound": claimed,
            "paper_bound_check_applicable": integer_releases,
            "observed_bound_violation": (maximum_ratio > claimed + 1e-8)
                if integer_releases and maximum_ratio is not None else None,
            "computed_trajectory_legs": self.computed_legs,
        }


def make_servers(config: Config) -> list[Server]:
    """Create exactly m servers, all on this one half-line."""
    return [Server(i, config.repairpersons) for i in range(1, config.repairpersons + 1)]


def parameters(m: int) -> tuple[float, float | None]:
    """Return the manuscript's alpha and beta for a local half-line count m."""
    Config(repairpersons=m)  # Keep count validation consistent for direct callers.
    if m == 1:
        return sqrt(3) / 2, None
    return 2 / (5 * m - 3), 5 / (5 * m - 3)


def claimed_halfline_bound(m: int) -> float:
    """The manuscript's stated bound, not a theorem certified by simulation."""
    Config(repairpersons=m)
    return 2 + sqrt(3) if m == 1 else max(1 + 8 / (5 * m - 3), 2)


def trip_targets(server: Server, trip: int) -> tuple[float, float]:
    """Direct translation of each role's (outward target, inward target).

    Targets are virtual nonnegative distances. A partial trip starts at the
    preceding inward target, not at the origin. Trip numbers are local to
    each server: the servers need not finish corresponding trips together.
    """
    if not isinstance(trip, int) or trip < 1:
        raise ValueError("Trip numbers must be positive integers.")
    alpha, beta = parameters(server.count)
    if not 1 <= server.id <= server.count:
        raise ValueError("Server ID must be a local rank in 1..m.")
    if server.count == 1:
        growth = 2 + 2 * alpha
        outward = growth / 2 if trip == 1 else growth ** (trip - 1) * (1 + 2 * alpha) / 2
        return outward, 0.0  # Algorithm 1, lines 4 and 6.
    assert beta is not None
    if server.id == 1:
        outward = beta if trip <= 2 else beta * 2.0 ** (trip - 2)
        return outward, 0.0  # Algorithm 2, lines 11 and 14: two equal initial trips.
    scale = 2.0 ** (trip - 1)
    if server.id == server.count:
        return scale, (1 - alpha) * scale  # Algorithm 2, line 5.
    return beta * server.id * scale, beta * (server.id - 1) * scale  # Line 6.


def _project_leg(virtual: Leg, length: float) -> Iterator[Leg]:
    """Set physical x(t)=min(virtual x(t),length), keeping the same timetable.

    Split at a boundary crossing so every output leg is either unit-speed
    movement or waiting. Early reversal would change future trip timings.
    """
    cuts = [virtual.t0, virtual.t1]
    boundary_time = None
    if min(virtual.x0, virtual.x1) < length < max(virtual.x0, virtual.x1):
        boundary_time = virtual.t0 + abs(length - virtual.x0)
        cuts.insert(1, boundary_time)
    for start, end in zip(cuts, cuts[1:]):
        if end <= start:  # A boundary interval below float time resolution.
            continue
        # A known boundary crossing is exactly at L. Interpolating it can
        # otherwise produce L-minus-one-ulp and delay an endpoint request.
        x0 = length if start == boundary_time else min(length, virtual.position_at(start))
        x1 = length if end == boundary_time else min(length, virtual.position_at(end))
        phase = "endpoint_wait" if x0 == x1 else virtual.phase
        yield Leg(start, end, x0, x1, virtual.trip, phase)


def schedule(server: Server, config: Config) -> Iterator[Leg]:
    """Infinite physical patrol, depending only on m, L, and local rank.

    Request locations, release times, and future request count never enter
    this function. Waiting occurs only because of endpoint projection.
    """
    if server.count != config.repairpersons:
        raise ValueError("Server count must match the half-line configuration.")
    time, position, trip = 0.0, 0.0, 1
    while True:
        outward, inward = trip_targets(server, trip)
        for target, phase in [(outward, "outward"), (inward, "inward")]:
            end = time + abs(target - position)
            if not isfinite(end) or end <= time:
                raise ArithmeticError("Schedule exceeds floating-point resolution; rescale units.")
            yield from _project_leg(Leg(time, end, position, target, trip, phase), config.length)
            time, position = end, target
        trip += 1


def validate_requests(requests: Sequence[Request], config: Config) -> None:
    if len({r.id for r in requests}) != len(requests):
        raise ValueError("Request IDs must be unique; repeated locations are allowed.")
    if any(not 0 <= r.position <= config.length for r in requests):
        raise ValueError("Every half-line position must lie in [0, length].")


def first_visit(request: Request, legs: Sequence[Leg], ends: Sequence[float],
                horizon: float) -> float | None:
    """Find the first eligible visit on one cached physical patrol.

    Binary search skips legs ending before release. Inspect one extra leg to
    handle roundoff when a release equals a computed turnaround timestamp.
    """
    start = max(0, bisect_left(ends, request.release) - 1)
    for index in range(start, len(legs)):
        leg = legs[index]
        if leg.t0 > horizon:
            break
        visit = leg.crossing(request.position, request.release)
        if visit is not None and visit <= horizon:
            return visit
    return None


def simulate(requests: Sequence[Request], config: Config = Config(), *,
             record_trajectories: bool = True) -> Simulation:
    """Evaluate first service exactly along piecewise-linear continuous patrols.

    Because the confirmed policy never reacts to requests, evaluating each
    request against these fixed schedules is equivalent to revealing requests
    during execution. It uses no future information to choose a movement.

    The observer extends a recording horizon until every request is served;
    the horizon never changes the policy or relies on a claimed bound. Each
    evaluation pass with J cached legs per server is O(n*m*J), avoiding a pending
    set scan at every request completion. Geometric schedules have few legs.
    """
    validate_requests(requests, config)
    servers = make_servers(config)
    paths: dict[int, list[Leg]] = {s.id: [] for s in servers}
    ends: dict[int, list[float]] = {s.id: [] for s in servers}
    streams = {s.id: schedule(s, config) for s in servers}
    completed: dict[int, Completion] = {}
    remaining = list(requests)
    horizon = max([1.0] + [max(r.release, r.position) for r in requests]) if requests else 0.0

    while remaining:
        for server in servers:
            while not ends[server.id] or ends[server.id][-1] < horizon:
                leg = next(streams[server.id])
                paths[server.id].append(leg)
                ends[server.id].append(leg.t1)
        unresolved = []
        for request in remaining:
            best: tuple[float, int] | None = None
            for server in servers:
                time = first_visit(request, paths[server.id], ends[server.id], horizon)
                if time is not None and (best is None or (time, server.id) < best):
                    best = time, server.id
            if best is None:
                unresolved.append(request)
            else:
                completed[request.id] = Completion(request, best[0], best[1])
        remaining = unresolved
        if remaining:
            horizon *= 2
            if not isfinite(horizon):
                raise ArithmeticError("Recording horizon overflowed; rescale the input units.")

    makespan = max((c.time for c in completed.values()), default=0.0)
    traces: dict[int, list[Leg]] = {s.id: [] for s in servers}
    distances = {}
    for server in servers:
        lengths = []
        for leg in paths[server.id]:
            if leg.t0 >= makespan:
                break
            end = min(leg.t1, makespan)
            last_position = leg.position_at(end)
            lengths.append(abs(last_position - leg.x0))
            if record_trajectories:
                traces[server.id].append(Leg(leg.t0, end, leg.x0, last_position, leg.trip, leg.phase))
        distances[server.id] = fsum(lengths)
    return Simulation(config, servers, [completed[r.id] for r in requests], traces,
                      distances, horizon, sum(len(path) for path in paths.values()))


def configuration_dict(config: Config) -> dict:
    alpha, beta = parameters(config.repairpersons)
    return {**asdict(config), "origin": 0, "domain": [0, config.length],
            "speed_when_moving": 1, "idle_policy": "continuous_patrol_from_time_zero",
            "boundary_policy": "time_preserving_endpoint_projection",
            "alpha": alpha, "beta": beta,
            "algorithm": "Algorithm 1 half-line" if config.repairpersons == 1 else "Algorithm 2 half-line",
            "corresponding_even_full_line_k": 2 * config.repairpersons}

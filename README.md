# Multi-Repairperson Online TRP: one half-line

This implementation simulates **m repairpersons on the physical interval
[0,L]**, all starting at zero at time zero. Every request and every physical
repairperson position is nonnegative. The count m is the number actually
simulated; it is never divided by two.

The confirmed policy patrols continuously, including periods without pending
requests. At the endpoint L, a repairperson waits while its virtual geometric
trajectory lies beyond L. This preserves the timetable from the paper.

The package includes readable source code, an exact small-instance offline
benchmark with the same m repairpersons, example request streams, plots,
reproducible experiments, and 25 correctness tests. `THEORY.md` explains the
half-line-to-full-line argument and records the remaining manuscript proof
issues. The algorithms and timing simulation contain no DDP or clustering
logic.

## 1. Run the included example

Use Python 3.10 or newer. The project was tested with Python 3.12.14. Extract
the ZIP, open a terminal, and enter the extracted `halfline_trp` folder:

```bash
cd halfline_trp
python run_simulation.py --input examples/requests.csv --length 10 --repairpersons 3 --offline exact --out results/first_run
```

On systems where the command is `python3`, substitute it for `python`. On
Windows, `py` can also be used. The commands work in a terminal opened in VS
Code or PyCharm as well.

Simulation, exact optimization, CSV/JSON output, and tests use only Python's
standard library. For figures, install the optional dependency and add `--plot`:

```bash
python -m pip install -r requirements.txt
python run_simulation.py --input examples/requests.csv --length 10 --repairpersons 3 --offline exact --plot --out results/first_plot
```

The physical domain in this example is **[0,10]**, with three repairpersons
all working on it. The corresponding equal-split full-line interpretation
would have k=6 repairpersons on [-10,10]. The program itself runs only [0,10].

Use a fresh `--out` directory for each experiment so output settings remain
easy to identify. Reusing an output directory overwrites files with matching
names; older optional files may remain if that option is omitted on a rerun.

## 2. Configure length, request count, and pattern

For 500 requests on [0,100] and two repairpersons on that half-line:

```bash
python run_simulation.py --length 100 --requests 500 --repairpersons 2 --arrival-horizon 100 --seed 7 --out results/n500_m2
```

`--arrival-horizon 100` means generated release times are integers from 0
through 100, inclusive. This is the last possible release time, **not** a
simulation cutoff. The recording horizon extends until every request is served.

| Option | Default | Meaning |
|---|---:|---|
| `--length L` | 100 | Physical endpoint; the domain is [0,L] |
| `--repairpersons m` | 3 | All m repairpersons operate on this one half-line |
| `--requests n` | 100 | Number of requests on the simulated half-line |
| `--arrival-horizon T` | 100 | Last possible generated integer release |
| `--pattern` | `uniform` | Workload distribution, described below |
| `--seed` | 7 | Local pseudorandom seed |
| `--input path.csv` | absent | Explicit request stream; overrides generation |
| `--offline` | `auto` | `auto`, `exact`, or `none` |
| `--exact-limit` | 10 | Request cap for the exponential offline solver |
| `--plot` | absent | Save a trajectory and request-ratio figure |
| `--no-trace` | absent | Omit the trajectory CSV; cannot be combined with `--plot` |
| `--out` | `results/run` | Directory for the run's outputs |

The confirmed endpoint and idle behavior are fixed in this implementation.
There are no `--idle`, `--boundary`, or full-line `--k` switches.

Available request patterns:

| Pattern | Definition and experimental purpose |
|---|---|
| `uniform` | Uniform positions in [0,L] and integer releases in [0,T] |
| `early` | All requests released at time zero; tests initial outward coverage |
| `bursty` | Releases at 0, floor(T/3), floor(2T/3), or T |
| `near_origin` | Uniform positions in [0,0.05L] |
| `near_endpoint` | Uniform positions in [0.95L,L] |
| `endpoints` | Requests at exactly 0 or L |
| `hotspots` | Gaussian neighborhoods of 0.1L, 0.5L, and 0.9L, clipped to [0,L] |

For example:

```bash
python run_simulation.py --length 50 --requests 200 --repairpersons 3 --pattern near_origin --arrival-horizon 200 --seed 12 --plot --out results/near_origin
```

Each generated request has its own ID. Repeated positions or release times
do not merge requests; each contributes separately to the objective.

## 3. Relate local m to the paper's full-line k

The paper partitions its k repairpersons into two groups. This program models
one such group directly:

| Local count m | Equal-split full-line k=2m | Half-line schedule |
|---:|---:|---|
| 1 | 2 | One side of Algorithm 1 |
| 2 | 4 | Algorithm 2 with alpha=2/7, beta=5/7 |
| 3 | 6 | Algorithm 2 with alpha=1/6, beta=5/12 |
| 4 | 8 | Algorithm 2 with alpha=2/17, beta=5/17 |
| 5 | 10 | Algorithm 2 with alpha=1/11, beta=5/22 |

For odd full-line k>=5, run the two needed local counts separately. For
example, k=5 uses m=2 on one side and m=3 on the other. Changing the sign of
the coordinates does not change either schedule's travel times. `THEORY.md`
derives the resulting whole-line bound without assuming that the two halves
have identical request streams.

## 4. Algorithm for m=1

This is the half-line component of Algorithm 1 on page 9. Set

\[
\alpha=\frac{\sqrt3}{2},\qquad q=2+2\alpha=2+\sqrt3.
\]

The outward turning distance on trip j is

\[
D_1=q/2=1+\alpha,\qquad
D_j=\frac{q^{j-1}(1+2\alpha)}{2}\quad(j\ge2).
\]

The virtual route is `0 -> D_j -> 0`. Its first turning distances are
approximately 1.8660, 5.0981, and 19.0263. Each new trip begins when the
previous return reaches zero. Completed round trips end at times q, q^2,
q^3, and so on.

The physical route is the projection of this virtual route onto [0,L]. For
example, let L=1. On the first trip, the repairperson reaches the physical
endpoint at time 1. It waits there while the virtual route moves to 1.8660
and back to 1, then returns to zero. It still finishes the trip at time
q, approximately 3.7321. Immediately reversing at L would change that
timetable and therefore implement a different policy.

In `halfline_trp.py`, `trip_targets()` implements the formulas, `schedule()`
produces unit-speed virtual legs, and `_project_leg()` converts them into
physical motion and endpoint waiting.

## 5. Algorithm for m>=2

This is Algorithm 2's half-line schedule, given on page 13. Set

\[
\alpha=\frac{2}{5m-3},\qquad
\beta=\frac{5}{5m-3},\qquad
\alpha+(m-1)\beta=1.
\]

Rank the repairpersons from S1 to Sm. This is a role assignment: all of them
initially occupy zero. The targets on trip j are:

| Role | Outward target | Inward target |
|---|---|---|
| S1, trips 1 and 2 | beta | 0 |
| S1, trips j>=3 | beta * 2^(j-2) | 0 |
| Si, 2<=i<=m-1 | beta * i * 2^(j-1) | beta * (i-1) * 2^(j-1) |
| Sm | 2^(j-1) | (1-alpha) * 2^(j-1) |

The middle-role row is empty when m=2. S1's first two trips deliberately have
the same size. Partial trips start where the previous trip ended, so the
middle and outer repairpersons do not return to the origin between trips.
Trip indices are local; the servers do not wait for one another to finish.

The outer role expands coverage to serve far requests. S1 repeatedly revisits
the origin and nearby points. Middle roles cover overlapping regions between
the inner and outer trajectories. Requests do not select a nearest server;
the first repairperson to visit after release serves the request.

For m=3, alpha=1/6 and beta=5/12. The first targets are:

| Repairperson | Outward | Inward |
|---|---:|---:|
| S1 | 5/12 | 0 |
| S2 | 5/6 | 5/12 |
| S3 | 1 | 5/6 |

S3 reaches 1 at time 1 and returns to 5/6 at time 7/6. Its next outward
leg reaches 2 at time 7/3. The following backtrack has distance 1/3,
ending at position 5/3 at time 8/3. These real-valued event times are kept
without rounding to integer steps.

## 6. How a request is served in the simulator

The confirmed patrol schedule never reacts to request arrivals. This allows
a simple and efficient evaluation of the online policy:

1. Validate that every request has a unique integer ID, nonnegative finite
   release time, and a position inside [0,L].
2. Build exactly m physical patrols from time zero, caching their linear
   movement and waiting intervals.
3. For each request, find the first visit at or after its release on each
   patrol. On a moving leg, solve the crossing time algebraically. On a
   waiting leg at the request's location, service is immediate upon release.
4. Choose the earliest eligible visit among the m repairpersons. Ties are
   resolved deterministically by server ID when computed times are equal.
5. Extend the observation horizon if any request is still unserved. Record
   trajectories and travel distance only through the last completion.

This is not a fixed-time-step simulation: a request at 0.37 can complete at
time 0.37. Release exactly at a visit or turnaround is eligible for service.
Several colocated released requests can complete simultaneously.

The observer uses the input to decide how long to evaluate the schedule. The
policy's targets and movements depend only on m, L, and the repairperson's
rank. Knowing future request values does not influence any movement. Evaluating
the fixed paths in a batch gives the same result as revealing requests during
the patrol; the tests verify this independence from future requests.

Useful code locations:

| Function or class | Role |
|---|---|
| `Request`, `Config` | Input model and confirmed conventions |
| `make_servers()` | Exactly m repairpersons; no side allocation |
| `parameters()` | Alpha and beta from the paper, using local m |
| `trip_targets()` | Algorithm 1 lines 4/6; Algorithm 2 lines 5/6/11/14 |
| `schedule()` | Timed geometric patrols |
| `_project_leg()` | Time-preserving endpoint waiting |
| `Leg.crossing()`, `first_visit()` | Service eligibility and exact linear crossing calculation |
| `simulate()` | Evaluation, horizon extension, and trajectory recording |
| `Simulation.metrics()` | Aggregate completion-time and delay metrics |
| `offline.exact_offline()` | Independent joint offline optimum on this same half-line |

For J cached legs per server, each evaluation pass costs O(n*m*J) in the
worst case; a binary search skips intervals ending before a request's release.
Patrols are cached across horizon extensions. Storage is O(n+m*J). The
geometric schedules need relatively few legs, and the included 1,000-request
run exercises the larger-input path without invoking exponential optimization.

## 7. Interpret the output

Write t_i for release time, x_i for position, and C_i for completion time.
The primary TRP objective is

\[
\operatorname{ON}_m(R)=\sum_i C_i.
\]

Flow time is C_i-t_i, the delay after release. Mean completion time, mean
flow time, makespan, and travel distance are also reported. The paper's
competitive bounds concern completion time; they do not automatically bound
flow time or distance by the same factor.

Every request has the individual optimum/lower bound

\[
\ell_i=\max\{t_i,x_i\},\qquad B(R)=\sum_i\ell_i\le\operatorname{OPT}_m(R).
\]

The offline optimum knows the entire input and may travel before a request
is released. Thus the individual bound is a maximum, not t_i+x_i.

| Output field | Interpretation |
|---|---|
| `total_completion_time` | Sum of absolute service times |
| `mean_completion_time` | Sum divided by request count |
| `mean_flow_time` | Mean post-release delay |
| `makespan` | Last service time |
| `total_distance_until_last_completion` | Physical movement of all m servers over that recording interval |
| `sum_individual_lower_bounds` | B(R), generally not the joint OPT |
| `online_over_lower_bound` | ON/B, an upper bound on this instance's ON/OPT |
| `max_request_over_lower_bound` | Largest observed C_i/ell_i |
| `offline_optimum` | Exact joint OPT with the same m repairpersons, when computed |
| `empirical_ratio_to_optimum` | ON/OPT for this particular input |
| `paper_claimed_halfline_bound` | Reference bound stated by the manuscript |

For positive denominators,

\[
\frac{\operatorname{ON}_m}{\operatorname{OPT}_m}
\le\frac{\operatorname{ON}_m}{B}
\le\max_i\frac{C_i}{\ell_i}.
\]

ON/B is a lower-bound-weighted average of the individual ratios. It is not
generally their arithmetic average. Zero-denominator ratios are `null` in
JSON and `n/a` in console output, and individual 0/0 terms are excluded from
request-ratio averages.

For example, release three requests at time 10 at positions 0, 1, and 2.
B=30, but the joint optima are 33 for m=1, 31 for m=2, and 30 for m=3.
Reproduce this with `examples/lower_bound_gap.csv`.

The reference half-line bound is

\[
\rho(m)=
\begin{cases}
2+\sqrt3,&m=1,\\
\max\{1+8/(5m-3),2\},&m\ge2.
\end{cases}
\]

It is approximately 3.732051 for m=1, 2.142857 for m=2, and 2 for m>=3.
The code labels it a manuscript claim. A finite sampled maximum or average
does not prove a universal competitive ratio. Noninteger CSV releases are
allowed for exploration, but disable comparison with the manuscript's
discrete-release bound. `THEORY.md` explains this qualification.

## 8. The exact offline benchmark

The benchmark receives the same `Config` as the online simulation, ensuring
that it has exactly m repairpersons and the same endpoint L. All offline
repairpersons start at zero at time zero. They can wait and pre-position
before releases. There is no requirement to follow the patrol targets or
return to zero after completing the requests.

The optimizer first finds the best single-server route for every request
subset. From position x at time t, appending a request at y with release r
gives service time `max(r, t+abs(y-x))`. It then partitions all requests
among at most m such routes to minimize their total cost.

For a fixed subset and final request, it retains every nondominated pair of
finish time and accumulated completion cost. A cheaper partial route can
finish later; retaining only its cost would lose a potentially optimal
continuation. This Pareto-label step is essential when there are release times.

Service on incidental crossings does not invalidate the route enumeration.
An actual optimal schedule induces first-service orders represented in the
enumeration, and its movements can be replaced by direct paths plus waiting
without delaying designated events. Conversely, any enumerated route is
feasible with actual services no later than its designated times. These two
directions establish equality of the optimized value and the actual optimum.
Direct paths and waits between positions in [0,L] stay in the physical domain.

The optimization is exponential. The default `--offline auto` solves up to
ten requests; larger inputs still get the online metrics and labeled lower
bounds. When m>=n, the optimizer can handle larger inputs by dedicating one
server to each request, attaining B. `--offline exact` makes exceeding the
input or label budget an explicit error. It never substitutes a heuristic
while labeling its result OPT.

"Exact" refers to combinatorial optimization; coordinate and cost arithmetic
uses floating-point numbers. `THEORY.md` documents numerical conventions.

## 9. Results already included

The eight requests in `examples/requests.csv` use L=10. Executed results are:

| m | Full-line context k=2m | Online sum | Exact half-line OPT_m | Online/OPT_m | Online/B |
|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 73.212813 | 57.300000 | 1.277711 | 1.743162 |
| 2 | 4 | 59.642857 | 42.000000 | 1.420068 | 1.420068 |
| 3 | 6 | 54.733333 | 42.000000 | 1.303175 | 1.303175 |

Online cost decreases here, while the ratio rises from m=1 to m=2 because
the offline optimum also changes. There is no requirement that empirical
ON/OPT decrease monotonically on every input as the number of servers changes.

For m=3, request 1 arrives at t=1, x=0.2. S1 completed its first round trip
at time `2*beta=5/6` and is moving outward again. It reaches 0.2 at
`5/6+0.2=1.033333`. The completion-cost contribution is 1.033333, and the
post-release delay is 0.033333.

Request 5 is released at the origin at time 7. S1 has just left zero after
its return at 20/3, so the request waits until its next return at 40/3.
Its completion is 13.333333, its flow time is 6.333333, and its individual
ratio is approximately 1.904762.

Each run writes:

| File | Contents |
|---|---|
| `requests.csv` | Exact input IDs, release times, and nonnegative positions |
| `completions.csv` | Each service time, delay, lower bound, ratio, and serving repairperson |
| `summary.json` | m, L, algorithm parameters, confirmed conventions, costs, and exact offline routes when solved |
| `trajectories.csv` | Physical movement/wait intervals through the last completion; omitted with `--no-trace` |
| `trajectories.png` | Figure created with `--plot` |

In the figure, `x` marks a release, a hollow circle marks service, and the
gray horizontal segment between them is the waiting interval. Colored paths
show the repairpersons. The vertical axis covers the single domain [0,L].

The `sample_results` folder also includes a 100-request paired sweep, an
eight-request sweep with exact OPT, a 1,000-request example, and a finite
bound audit. `sample_results/RESULTS.md` lists their settings and results.

## 10. Supply your own stream or call the Python API

Create a CSV with the exact columns below:

```csv
id,release_time,position
0,0,8
1,1,2.5
2,4,1
3,4,1
4,7,0
```

Then run:

```bash
python run_simulation.py --input my_requests.csv --length 10 --repairpersons 2 --offline exact --plot --out results/my_input
```

Requests need not be sorted. IDs must be unique integers. Positions outside
[0,L], negative releases, and nonfinite values are rejected. `--input`
overrides request generation; the length and repairperson-count settings
still define the model and benchmark.

From Python or a notebook whose working directory is `halfline_trp`:

```python
from halfline_trp import Config, Request, simulate
from offline import exact_offline

config = Config(length=20, repairpersons=3)
requests = [Request(0, 0, 4), Request(1, 3, 2), Request(2, 6, 0)]

run = simulate(requests, config)
opt = exact_offline(requests, config)
print(run.metrics())
print("Online / OPT:", run.metrics()["total_completion_time"] / opt.total_completion_time)
for completion in run.completions:
    print(completion.request.id, completion.time, completion.server)
```

`Request(id, release, position)` follows that argument order. Server IDs are
one-based: 1 through m, displayed as S1 through Sm in CSV files and plots.

## 11. Run paired experiments

Each value of m should see the same requests within a trial. This command
compares five local counts on ten inputs using seeds 7 through 16:

```bash
python run_experiments.py --repairpersons 1 2 3 4 5 --requests 100 --length 100 --arrival-horizon 100 --trials 10 --seed 7 --plot --out results/paired_sweep
```

For exact OPT comparisons, keep request counts small:

```bash
python run_experiments.py --repairpersons 1 2 3 4 --requests 8 --length 100 --arrival-horizon 100 --trials 10 --seed 7 --exact --plot --out results/exact_sweep
```

The sweep saves `experiment.json`, every trial's input, a `trials.csv` row
for each configuration, and `aggregate.csv`. Reported error bars are sample
standard deviations across trial-level ratios, not confidence intervals.

For a research evaluation, vary m, n, L, release horizon T, and workload
pattern. The ratio T/L affects how much the completion objective is dominated
by release times; report flow time alongside the completion ratios. Include
origin and endpoint patterns to expose revisitation delays and the effect of
endpoint waiting. Ten seeds form a reproducible example rather than a complete
statistical evaluation.

To search a finite grid for large individual ratios:

```bash
python audit_bounds.py --repairpersons 1 2 3 4 --length 100 --max-release 100 --spatial-step 1 --out results/bound_audit
```

The audit includes points immediately beside physical turns, saves one
witness CSV per m, and reruns each witness alone to verify its service time.
A non-violation on this finite grid is not a proof of competitiveness.

## 12. Verify correctness and migrate old settings

Run the standalone suite:

```bash
python -m unittest discover -s tests -v
```

The 25 tests check local counts, parameter formulas, exact endpoint behavior,
fractional and simultaneous service, duplicate and origin requests, unit-speed
feasibility, non-anticipation, reflection, input validation, CSV roundtrips,
and exact OPT against an exhaustive assignment/permutation oracle.

The regression fixture contains 15 cases generated using the previous full-line
implementation with `k=2m` and full length `2L`. Its right-side service times
and distances match this half-line implementation. The fixture stores only
nonnegative input data and expected outputs; the old code is not required to
run the tests.

| Previous full-line setting | Equivalent setting for its right half |
|---|---|
| `--length 100`, domain [-50,50] | `--length 50`, domain [0,50] |
| `--k 2` | `--repairpersons 1` |
| `--k 4` | `--repairpersons 2` |
| `--k 6` | `--repairpersons 3` |
| `--scenario uniform` | `--pattern uniform` on the nonnegative domain |
| Number of requests over both halves | Count requests belonging to the half being studied |

To reproduce an old right-side input, select its nonnegative requests with
their original release times. To reproduce an old left-side input, select
that side and reflect its coordinates. Taking the absolute value of every
request from both sides merges two workloads into one and changes the instance.

See `THEORY.md` for the precise reflection and full-line competitive argument.
The supplied TRP manuscript is the algorithm source; the implementation uses
its pseudocode target coordinates and explicitly documents proof-text
inconsistencies rather than treating experimental results as proof repairs.

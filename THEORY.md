# Theory and implementation decisions

This note accompanies the single-half-line implementation of the supplied
manuscript, *Multi-Repairperson Online TRP on a Line*. Page references below
use the manuscript's printed page numbers. `README.md` contains the commands,
algorithm formulas, code map, and output walkthrough.

## 1. The model implemented

The physical domain is the bounded half-line segment [0,L], with L>0. There
are m>=1 repairpersons, all at zero at time zero. Speed is at most one;
service is instantaneous and occurs on the first visit at or after release.
Request i has release time t_i>=0 and coordinate x_i in [0,L]. Its completion
time C_i is measured from time zero. The objective is the sum of C_i.

The following choices were confirmed for this rebuild:

- m is the actual number on this one half-line. No division by two occurs
  inside the algorithm or its offline benchmark.
- Patrols run continuously from time zero, including periods with no pending
  requests. Arrivals never pause, restart, or redirect a patrol.
- The geometric timetable is retained when a virtual target exceeds L.
  The physical repairperson waits at L until that virtual path reenters [0,L].

For m=1 the schedule is the half-line component of Algorithm 1 (page 9).
For m>=2 it uses Algorithm 2 (page 13), with its local group size replaced
by m. All geometric scales in the pseudocode are retained. L sets an endpoint;
it does not rescale the first outward target or the time unit.

## 2. Why endpoint waiting is a valid restriction

Let v_s(t)>=0 be a repairperson's unbounded virtual trajectory from the
pseudocode. Define its physical trajectory by

\[
x_s(t)=P_L(v_s(t)),\qquad P_L(z)=\min\{z,L\}.
\]

Projection P_L is 1-Lipschitz, so

\[
|x_s(t)-x_s(u)|\le |v_s(t)-v_s(u)|\le |t-u|.
\]

The projected route is feasible at speed at most one. For an interior
position d<L, its visit times are unchanged: P_L(v_s(t))=d exactly when
v_s(t)=d. For d=L, every original visit remains a visit, and the intervals
with v_s(t)>L provide additional service opportunities at L. Projection
therefore cannot worsen any request's completion time compared with the
virtual schedule for that same request stream in [0,L].

This observation transfers any valid per-request upper bound for the
unbounded timetable to the confirmed bounded implementation. It does not
require an offline repairperson to follow the patrol or to wait at L.

An immediate physical reversal at L would be another algorithm: subsequent
trip start times would move earlier. `_project_leg()` instead splits a virtual
leg at its boundary crossing, retaining its original start and finish times.

## 3. Reflection gives the other half

Define the reflected request stream

\[
R^- = \{(t_i,-x_i):(t_i,x_i)\in R^+\}.
\]

For every positive-side trajectory x_s(t), use y_s(t)=-x_s(t) on [-L,0].
Reflection preserves distances, start positions, speed, release times, and
the condition for serving each corresponding request. Thus, with the same m,

\[
C_i(R^+)=C_i(R^-),\qquad
\operatorname{ON}_m(R^+)=\operatorname{ON}_m(R^-).
\]

The same transformation is a bijection between feasible offline schedules on
the two separate half-lines. Consequently their local offline optima also
agree, and their corresponding local online/OPT ratios agree.

This is a pathwise statement for reflected inputs. Arbitrary left and right
request streams need not produce the same empirical numbers. Symmetric
sampling distributions imply corresponding distributional statements when
the server counts are equal; they do not make independently sampled runs
identical. For an odd full-line k, the two different local counts must also
be accounted for.

## 4. From a per-request half-line bound to a full-line bound

Let k=2, or k>=4. Allocate

\[
m_- = \lfloor k/2\rfloor,\qquad m_+=\lceil k/2\rceil.
\]

For k=2 both groups use the m=1 schedule. For k>=4 both group sizes are at
least two and use Algorithm 2's local schedule. Run the two groups
independently, reflecting the negative group's coordinates.

Partition requests between the two sides, assigning each request at the
origin to one side for accounting. An origin request remains one request;
it is not counted twice. If either group actually reaches the origin sooner,
the full-line algorithm can serve it then, only decreasing the accounted cost.

Define the individual lower bound

\[
\ell_i=\max\{t_i,|x_i|\}.
\]

Every feasible full-line offline solution starting all repairpersons at the
origin has C_i>=ell_i, even if its servers cross the origin or change sides.
Thus sum_i ell_i <= OPT_full,k.

**Suppose the local schedule has a proved per-request bound**

\[
C_i\le\rho(m_{\mathrm{side}(i)})\ell_i
\]

for every allowed release time and position. The full-line algorithm then
satisfies

\[
\begin{aligned}
\operatorname{ON}_{\mathrm{full},k}
&\le \sum_i \rho(m_{\mathrm{side}(i)})\ell_i\\
&\le \max\{\rho(m_-),\rho(m_+)\}\sum_i\ell_i\\
&\le \max\{\rho(m_-),\rho(m_+)\}\operatorname{OPT}_{\mathrm{full},k}.
\end{aligned}
\]

The manuscript claims

\[
\rho(m)=\begin{cases}
2+\sqrt3,&m=1,\\
\max\{1+8/(5m-3),2\},&m\ge2.
\end{cases}
\]

These values are nonincreasing in m, so the maximum is the smaller group's
value. Conditional on the local claim being proved, this recovers the
manuscript's k=2 value and, for k>=4,

\[
\max\left\{1+\frac{8}{5\lfloor k/2\rfloor-3},2\right\}.
\]

For example, k=5 uses m=2 and m=3, giving the reference value 15/7 from the
smaller group. The simulator accepts either local count directly; it never
silently maps an input m to floor(m/2).

The displayed implication is an algebraic reduction. The finite experiments
in this package support testing the local claim but do not prove its premise.
The manuscript proof issues recorded below remain relevant before a theorem
is stated as established in a revised paper.

## 5. Why local OPT ratios alone do not prove the whole-line guarantee

Write OPT_-(R_-) and OPT_+(R_+) for the optimal costs with fixed local server
allocations and each group restricted to its own side. Combining these two
schedules is feasible on the whole line, so

\[
\operatorname{OPT}_{\mathrm{full},k}
\le \operatorname{OPT}_{-}(R_-)+\operatorname{OPT}_{+}(R_+).
\]

This is the wrong inequality direction for deriving an upper bound on
ON_full/OPT_full from local ON/OPT ratios. An unrestricted full-line optimum
may allocate its effort differently between the sides. The per-request
lower-bound argument in Section 4 avoids that difficulty.

For two mirrored copies with equal groups, the online cost doubles if each
copy's requests are counted separately and there is no shared-origin counting
issue. Do not assume that the unrestricted whole-line optimum also doubles.
The experiments report the true local comparator, OPT_m on [0,L], and never
label it as the unrestricted full-line optimum.

## 6. Completion time, flow time, and the benchmark

Completion time C_i and flow time C_i-t_i measure different objectives. A
completion-time competitive ratio does not automatically yield the same
ratio for flow time, particularly when release times dominate the objective.

For a single request on the half-line, an offline repairperson can arrive
by its release if x_i<=t_i; otherwise it can arrive at time x_i. Hence the
single-request optimum is ell_i=max(t_i,x_i). For a stream,

\[
B=\sum_i\ell_i\le\operatorname{OPT}_m.
\]

The individual minima may not be simultaneously attainable with m servers.
For three requests released at 10 at positions 0, 1, and 2, B=30, while
OPT_1=33, OPT_2=31, and OPT_3=30. The included `lower_bound_gap.csv` exposes
this distinction.

`offline.py` performs joint optimization by enumerating single-server
request orders with Pareto labels for completion time and accumulated cost,
then partitioning requests among at most m routes. Unused repairpersons
are allowed. The optimizer may pre-position before release and has no final
return requirement. The small-instance tests compare its value with a
separate exhaustive assignment/permutation oracle.

For B>0, ON/OPT_m<=ON/B. The former is an empirical competitive ratio for
one instance; the latter is an upper bound on that ratio using a lower bound
on OPT. Neither a trial average nor a sampled maximum is a worst-case theorem.

## 7. Release-time convention and the first patrol

Section 2 of the manuscript specifies requests at discrete time steps.
The geometric routes have fractional turn times, so this implementation
uses integer releases in its generated workloads and continuous movement
and service times. There is no rounding of service to integer ticks.

This release convention matters for a patrol that starts at time zero.
For m=1, an origin request released at a small positive time epsilon waits
until the first return, q=2+sqrt(3). Its individual ratio is q/epsilon,
which is unbounded as epsilon tends to zero. The manuscript's claimed
constant therefore cannot simply be extended to arbitrary positive real
release times under this confirmed patrol convention.

Custom CSV files may contain real release times for exploration. In that
case `paper_bound_check_applicable` is false; the actual service metrics and
the exact local offline benchmark are still meaningful. Changing the unit
of distance alone does not rescale the integer release-time convention.

The confirmed policy also moves before the first request. For the included
`late_first_request.csv`, with m=3 and a sufficiently large L, the request
(t=1,x=1.001) is served at approximately 1.334333. Starting all servers only
at time 1 would yield a different trajectory and is not the implemented model.

## 8. Pseudocode precedence and manuscript proof issues

The executable targets follow the coordinates in Algorithms 1 and 2.
The following discrepancies in the supplied version should be addressed
when editing the proof. They are not settings left unresolved in the code.

1. **Outer repairperson's backtrack length.** Algorithm 2, line 5 (page 13)
   moves from 2^(j-1) to (1-alpha)2^(j-1). The distance is alpha*2^(j-1).
   The opening paragraph of the Lemma 1 proof (page 18) instead gives
   alpha*2^(j-2) for j>=2. The code uses the pseudocode endpoints.
2. **Invalid inequalities in Lemma 1's proof.** Page 18 uses
   (1+alpha)/(1-alpha)<=1+alpha and 1-alpha>=1. Both are false for
   0<alpha<1. These particular steps cannot justify the claimed bound.
3. **An intermediate simplification in Corollary 2.** Page 15 claims
   (1+4beta)/(1+4alpha)<=1+4alpha after substituting the selected parameters.
   At m=4, alpha=2/17 and beta=5/17, the left side is 37/25=1.48 and the
   right side is 25/17, approximately 1.470588. The inequality fails.
   This is not itself a counterexample to the final max-with-2 bound:
   both quantities in this example are below 2.

These observations identify specific proof repairs to investigate; they
are not a complete proof audit or a claim that the final theorem is false.
The code records the stated constants as `paper_claimed_halfline_bound`
and reports whether a tested input violates them. It does not certify the
manuscript's proof based on non-violations.

The DDP paper and cluster implementation are reference attachments only;
their algorithms and dependencies are not used in this package.

## 9. Numerical precision and validation evidence

Trajectories use analytic linear crossings, avoiding fixed-time-step
discretization. Coordinates and times are IEEE floating-point values, so
"exact offline" means exact combinatorial search using floating arithmetic,
not symbolic arithmetic over all coordinates.

`Leg.crossing()` allows eight floating-point units (ulps) when a computed
visit and release represent the same event to numerical precision. It never
reports service before release. This may merge genuinely distinct times
closer than that tolerance; it is not suitable for distinguishing adversarial
events separated by less than floating-point resolution. No fixed spatial
epsilon turns nearby requests into colocated requests.

Known endpoint crossings map to exactly L. This prevents roundoff from
creating a spurious slow-moving leg near L instead of a waiting interval.
The bound comparison uses absolute slack 1e-8. The finite audit probes
turning-point neighborhoods with offset 1e-7. These values and full-precision
inputs are saved with the results.

The 25 tests include geometric targets and durations, first-visit service,
speed feasibility, endpoint waits, tiny positive positions, non-anticipation,
reflection, validation, and offline-oracle comparisons. A saved fixture of
15 previous full-line runs checks that, with full length 2L and k=2m, the
right group's service times and distance equal this implementation's results.
The new test suite is independent of the previous source files.

The finite audit tests 56,758 release-position pairs across m=1,2,3,4 and
reruns each largest-ratio witness alone. No violation was observed on that
grid. Reproduction commands and exact settings are in
`sample_results/RESULTS.md`; this empirical evidence is separate from the
conditional full-line derivation above.

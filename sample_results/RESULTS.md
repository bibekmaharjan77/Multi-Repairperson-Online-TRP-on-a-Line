# Executed half-line experiments

These are executed results from this package, using Python 3.12.14. Every
run places all m repairpersons on [0,L], begins continuous patrol at time
zero, and uses time-preserving endpoint waiting. The physical speed is one.
No full-line simulation is used to produce the tables below.

Use the commands from the parent `halfline_trp` directory. Matplotlib is
needed only when `--plot` is present. Full-precision inputs and measurements
are stored beside this note. Values displayed here are rounded.

## Eight-request walkthrough

The input is `examples/requests.csv`, with L=10 and B=sum max(t_i,x_i)=42.
Each m receives exactly the same eight requests.

```bash
python run_simulation.py --input examples/requests.csv --length 10 --repairpersons 1 --offline exact --plot --out sample_results/walkthrough_m1
python run_simulation.py --input examples/requests.csv --length 10 --repairpersons 2 --offline exact --plot --out sample_results/walkthrough_m2
python run_simulation.py --input examples/requests.csv --length 10 --repairpersons 3 --offline exact --plot --out sample_results/walkthrough_m3
```

| m | Online completion sum | Exact local OPT_m | Online/OPT_m | Online/B | Makespan |
|---:|---:|---:|---:|---:|---:|
| 1 | 73.212813 | 57.300000 | 1.277711 | 1.743162 | 23.928203 |
| 2 | 59.642857 | 42.000000 | 1.420068 | 1.420068 | 18.571429 |
| 3 | 54.733333 | 42.000000 | 1.303175 | 1.303175 | 15.000000 |

The online cost decreases across these counts, but the first empirical ratio
is smaller than the second because their offline comparators differ. An
empirical ratio should be interpreted with its m, input, and objective.

For m=3, the per-request completions are:

| ID | Release | Position | Completion | Repairperson |
|---:|---:|---:|---:|---|
| 0 | 0 | 1 | 1.000000 | S3 |
| 1 | 1 | 0.2 | 1.033333 | S1 |
| 2 | 2 | 0.3 | 3.033333 | S1 |
| 3 | 3 | 4 | 5.000000 | S3 |
| 4 | 5 | 4 | 5.000000 | S3 |
| 5 | 7 | 0 | 13.333333 | S1 |
| 6 | 10 | 2 | 11.333333 | S1 |
| 7 | 12 | 10 | 15.000000 | S3 |

See `walkthrough_m3/trajectories.png` for patrols, releases, services, and
waiting intervals, and its `summary.json` for an optimal offline route set.

## Paired sweep with 100 requests

This sweep uses uniform positions in [0,100], integer releases in [0,100],
100 requests per trial, ten trials, and seeds 7 through 16. Within each trial,
all m values receive the same request stream. Saved `inputs/trial_*.csv`
files make the pairing inspectable.

```bash
python run_experiments.py --repairpersons 1 2 3 4 5 --requests 100 --length 100 --arrival-horizon 100 --trials 10 --seed 7 --plot --out sample_results/paired_sweep
```

| m | Mean Online/B | Sample standard deviation | Largest request C_i/max(t_i,x_i) observed |
|---:|---:|---:|---:|
| 1 | 2.249038 | 0.087933 | 3.724223 |
| 2 | 1.595427 | 0.037297 | 2.132331 |
| 3 | 1.355971 | 0.019532 | 1.973565 |
| 4 | 1.281944 | 0.014960 | 1.897925 |
| 5 | 1.224516 | 0.010623 | 1.866776 |

Exact OPT was not computed for these 100-request instances. The table's
Online/B column uses a lower bound on OPT; it is an upper bound on each
trial's true empirical ratio before taking the average. The last column is
the largest individual ratio across all ten inputs, not a proved worst case.

`paired_sweep/comparison.png` displays these averages with one sample
standard deviation error bars. The bars are not confidence intervals.

## Paired sweep with exact offline optima

This sweep keeps the same L, release horizon, pattern, and seed range, but
uses eight requests per trial so joint offline optimization is practical.

```bash
python run_experiments.py --repairpersons 1 2 3 4 --requests 8 --length 100 --arrival-horizon 100 --trials 10 --seed 7 --exact --plot --out sample_results/exact_sweep
```

| m | Mean Online/OPT_m | Sample standard deviation | Mean Online/B |
|---:|---:|---:|---:|
| 1 | 1.718578 | 0.231816 | 2.242878 |
| 2 | 1.541744 | 0.162550 | 1.572790 |
| 3 | 1.347244 | 0.066629 | 1.348860 |
| 4 | 1.313167 | 0.058165 | 1.313167 |

Each mean averages trial-level ratios; it is not the ratio of aggregated
costs. The differing Online/OPT and Online/B columns quantify the looseness
of the individual-request lower bound on these inputs. They coincide for
m=4 in these trials because the joint optimum attains B on these instances.

## One larger run

```bash
python run_simulation.py --requests 1000 --length 100 --repairpersons 3 --arrival-horizon 100 --seed 7 --no-trace --out sample_results/n1000
```

| Measurement | Value |
|---|---:|
| Requests | 1,000 |
| Online completion sum | 89,304.601601 |
| B | 65,661.408254 |
| Online/B | 1.360077 |
| Mean completion time | 89.304602 |
| Mean flow time | 39.676602 |
| Largest individual request ratio | 1.966451 |
| Makespan | 142.320709 |

The run stops recording at the last completion, after the final possible
release time of 100. Exact OPT is uncomputed, and `--no-trace` omits the
exported trajectories. No runtime benchmark is claimed from this single run.

## Finite per-request bound audit

```bash
python audit_bounds.py --repairpersons 1 2 3 4 --length 100 --max-release 100 --spatial-step 1 --out sample_results/bound_audit
```

The audit enumerates integer release times from 0 through 100 and positions
on a unit grid, augmented with physical turning locations and offsets of
1e-7 on either side when inside the domain. Because the policy is independent
of requests, these pairs can be evaluated together. Each selected witness is
also rerun alone to check that independence.

| m | Pairs tested | Largest observed ratio | Witness release | Witness position | Manuscript reference bound |
|---:|---:|---:|---:|---:|---:|
| 1 | 11,614 | 3.732050808 | 1 | 0 | 3.732050808 |
| 2 | 14,240 | 2.142857093 | 2 | 1.428571329 | 2.142857143 |
| 3 | 14,240 | 1.975308642 | 27 | 0 | 2 |
| 4 | 16,664 | 1.981424149 | 19 | 0 | 2 |

No violation was observed among these 56,758 pairs, using comparison slack
1e-8. `bound_audit/audit.csv` stores full-precision witness values and settings;
`witness_m*.csv` stores independently runnable requests.

This finite grid does not cover all positions, all integer releases, all
lengths, or all m. It does not repair or certify the proof steps discussed
in `THEORY.md`.

## What these experiments support

These runs demonstrate reproducible simulation on a single nonnegative
domain, first-visit service at fractional times, meaningful local offline
comparisons, and paired comparisons between repairperson counts. The
25-test suite additionally validates reflection and matches 15 saved
right-side cases from the earlier full-line implementation.

For a paper's experimental section, identify the policy conventions, local
server count, L, release horizon, request pattern, seeds, and comparator.
Use "empirical Online/OPT" only when joint OPT was computed. Refer to
Online/B explicitly as a lower-bound comparison. The reflection argument
transfers corresponding half-line behavior to the opposite side; a universal
full-line competitive statement additionally requires the per-request bound
proved under the stated model.

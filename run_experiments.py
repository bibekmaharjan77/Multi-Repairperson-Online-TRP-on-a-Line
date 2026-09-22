"""Compare actual half-line repairperson counts on paired, seeded workloads."""

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

from halfline_trp import Config, simulate
from offline import exact_offline
from reporting import attach_offline_metrics
from workloads import PATTERNS, generate_requests, write_requests


def write_table(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repairpersons", type=int, nargs="+", default=[1, 2, 3, 4],
                        help="Counts m to compare, all on the single half-line.")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--length", type=float, default=100)
    parser.add_argument("--arrival-horizon", type=int, default=100)
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--seed", type=int, default=7, help="Trial i uses seed+i.")
    parser.add_argument("--pattern", choices=PATTERNS, default="uniform")
    parser.add_argument("--exact", action="store_true", help="Joint OPT with the same m; <=10 requests unless every m>=n.")
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("results/sweep"))
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials must be positive.")
    counts = sorted(set(args.repairpersons))
    try:
        configs = [Config(args.length, m) for m in counts]
        if args.exact and args.requests > 10 and min(counts) < args.requests:
            parser.error("Exact sweep requires <=10 requests unless every m>=n.")
        # Validate workload arguments before writing any experiment output.
        generate_requests(args.requests, args.length, args.arrival_horizon, args.seed, args.pattern)
        args.out.mkdir(parents=True, exist_ok=True)
        input_dir = args.out / "inputs"
        input_dir.mkdir(exist_ok=True)
        metadata = {**vars(args), "out": str(args.out), "repairpersons": counts,
                    "python": sys.version.split()[0], "domain": [0, args.length],
                    "idle_policy": "continuous_patrol_from_time_zero",
                    "boundary_policy": "time_preserving_endpoint_projection"}
        (args.out / "experiment.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        rows = []
        for trial in range(args.trials):
            seed = args.seed + trial
            requests = generate_requests(args.requests, args.length, args.arrival_horizon, seed, args.pattern)
            write_requests(input_dir / f"trial_{trial:03d}.csv", requests)
            for config in configs:
                simulation = simulate(requests, config, record_trajectories=False)
                optimum = exact_offline(requests, config) if args.exact else None
                metrics = attach_offline_metrics(simulation.metrics(), optimum,
                                                "exact (floating-point arithmetic)" if optimum else "not requested")
                rows.append({"trial": trial, "seed": seed, "pattern": args.pattern,
                             "arrival_horizon": args.arrival_horizon, **metrics})
        write_table(args.out / "trials.csv", rows)
        summary = []
        for m in counts:
            group = [row for row in rows if row["repairpersons"] == m]
            item = {"repairpersons": m, "corresponding_even_full_line_k": 2 * m,
                    "trials": args.trials,
                    "paper_claimed_halfline_bound": group[0]["paper_claimed_halfline_bound"]}
            for metric in ["online_over_lower_bound", "empirical_ratio_to_optimum",
                           "mean_completion_time", "mean_flow_time"]:
                values = [row[metric] for row in group if row[metric] is not None]
                item[metric + "_mean"] = statistics.mean(values) if values else None
                item[metric + "_std"] = statistics.stdev(values) if len(values) > 1 else (0.0 if values else None)
            maxima = [row["max_request_over_lower_bound"] for row in group
                      if row["max_request_over_lower_bound"] is not None]
            item["worst_observed_request_ratio"] = max(maxima, default=None)
            item["observed_bound_violations"] = sum(row["observed_bound_violation"] is True for row in group)
            summary.append(item)
        write_table(args.out / "aggregate.csv", summary)
        if args.plot:
            plot_comparison(args.out, summary, args)
        for row in summary:
            value = row["online_over_lower_bound_mean"]
            label = "n/a" if value is None else f"{value:.6f}"
            print(f"m={row['repairpersons']}: mean Online/LB={label}; "
                  f"max observed request/LB={row['worst_observed_request_ratio']}")
        print(f"Paired half-line inputs and results: {args.out.resolve()}")
    except (ValueError, ArithmeticError, OSError, ImportError) as error:
        parser.exit(2, f"Error: {error}\n")


def plot_comparison(output: Path, rows: list[dict], args: argparse.Namespace) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 5.5), constrained_layout=True)
    counts = [row["repairpersons"] for row in rows]
    for metric, color, marker, label in [
        ("online_over_lower_bound", "#2563eb", "o", "Online / LB: mean +/- sample SD"),
        ("empirical_ratio_to_optimum", "#059669", "s", "Online / exact OPT: mean +/- sample SD"),
    ]:
        if any(row[metric + "_mean"] is not None for row in rows):
            ax.errorbar(counts, [row[metric + "_mean"] for row in rows],
                        yerr=[row[metric + "_std"] for row in rows],
                        marker=marker, capsize=4, color=color, label=label)
    if any(row["worst_observed_request_ratio"] is not None for row in rows):
        ax.plot(counts, [row["worst_observed_request_ratio"] for row in rows],
                marker="^", color="#9333ea", label="Worst observed request / LB")
    ax.plot(counts, [row["paper_claimed_halfline_bound"] for row in rows], "--",
            color="#dc2626", label="Manuscript claimed half-line bound")
    ax.set(xlabel="Repairpersons m on the simulated half-line", ylabel="Ratio",
           title=f"Half-line [0, {args.length:g}] | {args.pattern} | n={args.requests} | {args.trials} paired trials\n"
                 f"Integer releases 0..{args.arrival_horizon}; continuous patrol; endpoint waiting")
    ax.set_xticks(counts)
    ax.grid(alpha=0.18)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=9)
    fig.savefig(output / "comparison.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()

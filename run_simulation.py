"""Run the confirmed half-line model: python run_simulation.py --help"""

import argparse
import sys
from pathlib import Path

from halfline_trp import Config, simulate
from offline import exact_offline
from reporting import plot_run, print_metrics, write_run
from workloads import PATTERNS, generate_requests, read_requests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--length", type=float, default=100, help="Half-line endpoint L; physical domain [0,L].")
    parser.add_argument("--repairpersons", type=int, default=3, help="Actual number m on this half-line, >=1; never divided by two.")
    parser.add_argument("--requests", type=int, default=100, help="Number of requests on this half-line.")
    parser.add_argument("--arrival-horizon", type=int, default=100, help="Largest generated integer release; not a simulation cutoff.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--pattern", choices=PATTERNS, default="uniform")
    parser.add_argument("--input", type=Path, help="CSV input overrides generated requests.")
    parser.add_argument("--offline", choices=["auto", "exact", "none"], default="auto",
                        help="auto solves <=10 requests or m>=n; larger inputs report lower bounds.")
    parser.add_argument("--exact-limit", type=int, default=10, help="Input cap for exponential OPT; increase carefully.")
    parser.add_argument("--plot", action="store_true", help="Save a PNG figure; requires Matplotlib.")
    parser.add_argument("--no-trace", action="store_true", help="Skip the trajectory CSV; incompatible with --plot.")
    parser.add_argument("--out", type=Path, default=Path("results/run"), help="Result directory; use a new directory for each experiment.")
    args = parser.parse_args()
    if args.plot and args.no_trace:
        parser.error("--plot needs recorded trajectories; omit --no-trace.")
    if args.exact_limit < 1:
        parser.error("--exact-limit must be positive.")
    try:
        config = Config(args.length, args.repairpersons)
        requests = read_requests(args.input) if args.input else generate_requests(
            args.requests, args.length, args.arrival_horizon, args.seed, args.pattern)
        simulation = simulate(requests, config, record_trajectories=not args.no_trace)
        offline, status = None, "disabled"
        solve = args.offline == "exact" or (args.offline == "auto" and (
            len(requests) <= args.exact_limit or args.repairpersons >= len(requests)))
        if solve:
            offline = exact_offline(requests, config, max_requests=args.exact_limit)
            status = "exact (floating-point arithmetic)"
        elif args.offline == "auto":
            status = f"not computed: n exceeds exact limit {args.exact_limit}"
        metadata = {"input": str(args.input) if args.input else "generated",
                    "pattern": args.pattern if not args.input else None,
                    "seed": args.seed if not args.input else None,
                    "arrival_horizon": args.arrival_horizon if not args.input else None,
                    "exact_limit": args.exact_limit, "python": sys.version.split()[0],
                    "trajectory_recording": not args.no_trace}
        metrics = write_run(args.out, simulation, offline, status, metadata)
        print_metrics(metrics)
        if args.plot:
            try:
                plot_run(args.out, simulation)
            except ImportError:
                parser.exit(1, "Data saved; plotting requires: python -m pip install matplotlib\n")
        print(f"Outputs: {args.out.resolve()}")
    except (ValueError, ArithmeticError, OSError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()

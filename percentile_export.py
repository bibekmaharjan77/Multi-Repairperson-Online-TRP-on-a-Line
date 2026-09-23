"""Prepare the mean percentile curve from ten completed TRP runs.

Expected input layout (one independent generated run per folder):

    results/paper_L100_m3/seed_10/tableau_requests.csv
    results/paper_L100_m3/seed_10/tableau_runs.csv  # optional metadata check
    ...
    results/paper_L100_m3/seed_19/tableau_requests.csv

The beginner runner's completions.csv + summary.json can be used instead of
tableau_requests.csv + tableau_runs.csv. If both request formats are present
in one seed folder, tableau_requests.csv takes precedence.

The request/completion CSV needs a Request Over Lower Bound or Valid Request
Ratio column.
Individual Lower Bound is used, when available, to count excluded zero-bound
requests. The output is small enough to import directly into Tableau.

Run after all ten simulations have finished:

    python percentile_export.py --root results/paper_L100_m3

Use --expected-requests N for a small practice run, or --expected-requests 0
to disable that check. No third-party packages are needed.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from statistics import fmean


RATIO_FIELDS = ("validrequestratio", "requestoverlowerbound")
LOWER_BOUND_FIELDS = ("individuallowerbound",)
PERCENTILES = sorted(
    set(range(101)) | {99.1, 99.2, 99.3, 99.4, 99.5, 99.6, 99.7,
                       99.8, 99.9, 99.95, 99.99, 99.999}
)


def normalized(name: str) -> str:
    """Treat spaces and underscores in CSV headers the same way."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def named_column(headers: list[str], choices: tuple[str, ...]) -> str | None:
    by_name = {normalized(name): name for name in headers}
    return next((by_name[name] for name in choices if name in by_name), None)


def seed_from_folder(path: Path) -> int | None:
    match = re.search(r"(?:^|[^a-z0-9])seed[_-]?0*(\d+)(?:$|[^a-z0-9])",
                      path.parent.name.lower())
    return int(match.group(1)) if match else None


def seed_from_runs_csv(path: Path) -> int | None:
    """Check run metadata before combining nominally identical experiments."""
    metadata_path = path.with_name("tableau_runs.csv")
    if not metadata_path.exists():
        return None
    with metadata_path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        name = named_column(reader.fieldnames or [], ("seed",))
        checks = (
            (("length", "halflinelength", "linelength"), 100.0),
            (("repairpersons",), 3),
            (("arrivalhorizon",), 100),
            (("pattern",), "uniform"),
        )
        rows = list(reader)
        if not rows:
            raise ValueError(f"No run records in {metadata_path}")
        for row in rows:
            for aliases, expected in checks:
                column = named_column(reader.fieldnames or [], aliases)
                if column is None or not row[column] or not row[column].strip():
                    continue  # Some exports do not include every setting.
                actual = row[column].strip()
                if isinstance(expected, str):
                    valid = actual.lower() == expected
                else:
                    try:
                        valid = float(actual) == expected
                    except ValueError:
                        valid = False
                if not valid:
                    raise ValueError(
                        f"{metadata_path}: {column}={actual!r}; this plot requires {expected!r}"
                    )
        if name is None:
            return None
        values = {row[name].strip() for row in rows if row[name] and row[name].strip()}
    if not values:
        return None
    if len(values) != 1:
        raise ValueError(f"Multiple seeds in {metadata_path}: {values!r}")
    try:
        return int(float(next(iter(values))))
    except ValueError as error:
        raise ValueError(f"Invalid seed in {metadata_path}: {values!r}") from error


def seed_from_summary_json(path: Path) -> int | None:
    """Validate the original beginner runner's experiment and configuration."""
    summary_path = path.with_name("summary.json")
    if not summary_path.exists():
        return None
    with summary_path.open(encoding="utf-8") as stream:
        summary = json.load(stream)
    settings = [
        (summary.get("configuration", {}), "length", 100.0),
        (summary.get("configuration", {}), "repairpersons", 3),
        (summary.get("experiment", {}), "arrival_horizon", 100),
        (summary.get("experiment", {}), "pattern", "uniform"),
    ]
    for section, name, expected in settings:
        actual = section.get(name)
        if actual is None:
            continue
        if actual != expected:
            raise ValueError(f"{summary_path}: {name}={actual!r}; expected {expected!r}")
    seed = summary.get("experiment", {}).get("seed")
    return int(seed) if seed is not None else None


def percentile(sorted_values: list[float], p: float) -> float:
    """Linear interpolation, with p=0 yielding min and p=100 yielding max."""
    index = (len(sorted_values) - 1) * p / 100
    lower = math.floor(index)
    upper = math.ceil(index)
    weight = index - lower
    return sorted_values[lower] + weight * (sorted_values[upper] - sorted_values[lower])


def read_run(path: Path, seed: int, expected_requests: int) -> tuple[dict, dict]:
    ratios: list[float] = []
    row_count = 0
    zero_bound = 0
    violations = 0
    ratio_sum = 0.0
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        ratio_col = named_column(headers, RATIO_FIELDS)
        bound_col = named_column(headers, LOWER_BOUND_FIELDS)
        if ratio_col is None:
            raise ValueError(
                f"{path} needs a 'Request Over Lower Bound' or 'Valid Request Ratio' column. "
                f"Found: {headers}"
            )
        for line_number, row in enumerate(reader, start=2):
            row_count += 1
            raw_bound = row[bound_col].strip() if bound_col and row[bound_col] else ""
            if raw_bound:
                bound = float(raw_bound)
                if not math.isfinite(bound) or bound < 0:
                    raise ValueError(f"Invalid lower bound at {path}:{line_number}")
                if bound == 0:
                    zero_bound += 1
                    continue
            raw_ratio = row[ratio_col].strip() if row[ratio_col] else ""
            if not raw_ratio:
                if bound_col is None or not raw_bound:
                    zero_bound += 1  # Missing ratio; verify whether its bound is zero.
                    continue
                raise ValueError(f"Missing ratio with positive lower bound at {path}:{line_number}")
            ratio = float(raw_ratio)
            if not math.isfinite(ratio) or ratio < 0:
                raise ValueError(f"Invalid ratio at {path}:{line_number}")
            ratios.append(ratio)
            ratio_sum += ratio
            violations += ratio > 2.0

    if expected_requests and row_count != expected_requests:
        raise ValueError(f"{path}: expected {expected_requests:,} requests, found {row_count:,}")
    if not ratios:
        raise ValueError(f"{path}: no valid per-request ratios")
    ratios.sort()
    values = {p: percentile(ratios, p) for p in PERCENTILES}
    summary = {
        "seed": seed,
        "total_requests": row_count,
        "valid_ratios": len(ratios),
        "excluded_zero_or_missing_bound": zero_bound,
        "mean_request_ratio": ratio_sum / len(ratios),
        "median_ratio": values[50],
        "p95_ratio": values[95],
        "p99_ratio": values[99],
        "max_ratio": ratios[-1],
        "requests_above_2": violations,
    }
    return values, summary


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True,
                        help="Folder containing separate seed_10 through seed_19 subfolders")
    parser.add_argument("--expected-requests", type=int, default=1_000_000,
                        help="Expected request rows in each run; 0 disables the count check")
    args = parser.parse_args()
    if args.expected_requests < 0:
        parser.error("--expected-requests must be nonnegative")
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"Not a directory: {root}")

    by_seed: dict[int, Path] = {}
    for source_name in ("completions.csv", "tableau_requests.csv"):
        for path in root.rglob(source_name):
            seed = seed_from_folder(path)
            if seed is None or seed not in range(10, 20):
                continue
            metadata_seed = (seed_from_summary_json(path) if source_name == "completions.csv"
                             else seed_from_runs_csv(path))
            if metadata_seed is not None and metadata_seed != seed:
                raise ValueError(f"Folder says seed {seed}, but {path.parent} metadata says {metadata_seed}")
            if seed in by_seed and by_seed[seed].name == source_name:
                raise ValueError(f"Two {source_name} files found for seed {seed}: {by_seed[seed]} and {path}")
            by_seed[seed] = path
    missing = sorted(set(range(10, 20)) - set(by_seed))
    if missing:
        raise ValueError(f"Missing tableau_requests.csv or completions.csv for seeds {missing} under {root}")

    seed_values: dict[int, dict] = {}
    per_seed_rows = []
    run_rows = []
    for seed, path in sorted(by_seed.items()):
        values, run = read_run(path, seed, args.expected_requests)
        seed_values[seed] = values
        run_rows.append(run)
        per_seed_rows.extend({"seed": seed, "cumulative_percent": p,
                              "ratio_at_percentile": ratio}
                             for p, ratio in values.items())
        print(f"Seed {seed}: {run['valid_ratios']:,} valid ratios; max={run['max_ratio']:.6f}")

    mean_rows = []
    for p in PERCENTILES:
        observed = [seed_values[seed][p] for seed in sorted(seed_values)]
        mean_rows.append({"cumulative_percent": p,
                          "mean_ratio_at_percentile": fmean(observed),
                          "min_ratio_at_percentile": min(observed),
                          "max_ratio_at_percentile": max(observed),
                          "number_of_runs": len(observed)})
    out = root / "plot_data"
    out.mkdir(exist_ok=True)
    write_csv(out / "mean_percentile_curve.csv", list(mean_rows[0]), mean_rows)
    write_csv(out / "per_seed_percentiles.csv", list(per_seed_rows[0]), per_seed_rows)
    write_csv(out / "run_checks.csv", list(run_rows[0]), run_rows)
    print(f"Tableau-ready CSVs: {out}")
    print("Plot X=mean_ratio_at_percentile, Y=cumulative_percent; mark type Line.")


if __name__ == "__main__":
    main()

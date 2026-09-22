"""CSV/JSON export and optional Matplotlib figures for reproducible experiments."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from offline import OfflineResult
from halfline_trp import Simulation, configuration_dict
from workloads import write_requests
 # Input: Matplotlib's plotting tools. Give them the shorter name plt.
import matplotlib.pyplot as plt
# Input: Matplotlib tick-formatting tools. Lets us control how axis numbers appear.
from matplotlib.ticker import FuncFormatter


def attach_offline_metrics(metrics: dict, offline: OfflineResult | None, status: str) -> dict:
    metrics = dict(metrics)
    metrics["offline_status"] = status
    opt = offline.total_completion_time if offline else None
    metrics["offline_optimum"] = opt
    metrics["empirical_ratio_to_optimum"] = (
        metrics["total_completion_time"] / opt if opt is not None and opt > 0 else None
    )
    return metrics


def write_run(output: Path, simulation: Simulation, offline: OfflineResult | None,
              offline_status: str, metadata: dict) -> dict:
    """Write complete inputs, conventions, metrics, per-request data, and paths."""
    output.mkdir(parents=True, exist_ok=True)
    metrics = attach_offline_metrics(simulation.metrics(), offline, offline_status)
    requests = [c.request for c in simulation.completions]
    write_requests(output / "requests.csv", requests)
    payload = {"configuration": configuration_dict(simulation.config),
               "experiment": metadata, "metrics": metrics,
               "servers": [{**asdict(s), "name": s.name, "role": s.role} for s in simulation.servers],
               "distance_by_server": simulation.distance_by_server}
    if offline:
        payload["offline_solution"] = asdict(offline)
    (output / "summary.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    names = {s.id: s.name for s in simulation.servers}
    with (output / "completions.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["id", "release_time", "position", "completion_time", "flow_time",
                         "individual_lower_bound", "request_over_lower_bound", "server"])
        for c in simulation.completions:
            lb = c.request.lower_bound
            writer.writerow([c.request.id, c.request.release, c.request.position, c.time,
                             c.time - c.request.release, lb, c.time / lb if lb else "", names[c.server]])

    #creation of two csv tableau_requests and tableau_runs for data visualization
    # Uses the results-folder name as the shared identifier for this simulation run.
    run_id = output.name
    # Reads configuration values, including the implemented half-line algorithm name.
    config = configuration_dict(simulation.config)

    # Stores one row containing settings and overall metrics for this run.
    run_row = {
        "run_id": run_id,
        "input_source": metadata.get("input"),
        "pattern": metadata.get("pattern"),
        "seed": metadata.get("seed"),
        "arrival_horizon": metadata.get("arrival_horizon"),
        "algorithm": config["algorithm"],
        **metrics,
    }
    # Opens a Tableau run-summary CSV file for writing.
    with (output / "tableau_runs.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=run_row.keys())  # Creates columns from the run-row names.
        writer.writeheader()  # Writes the first row of column names.
        writer.writerow(run_row)  # Writes the one summary row for this run.

    # Opens a Tableau request-level CSV file for writing.
    with (output / "tableau_requests.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)  # Creates a CSV writer.
        writer.writerow([  # Writes names for one row per request.
            "run_id", "request_id", "release_time", "position",
            "completion_time", "flow_time", "individual_lower_bound",
            "request_over_lower_bound", "server", "repairpersons",
            "halfline_length", "corresponding_full_line_k", "algorithm",
            "input_source", "pattern", "seed", "arrival_horizon",
        ])
        for completion in simulation.completions:  # Repeats once for every completed request.
            request = completion.request  # Gets the original request data.
            lower_bound = request.lower_bound  # Gets max(release time, position).
            writer.writerow([  # Writes one Tableau-ready request record.
                run_id, request.id, request.release, request.position,
                completion.time, completion.time - request.release,
                lower_bound, completion.time / lower_bound if lower_bound else "",
                names[completion.server], simulation.config.repairpersons,
                simulation.config.length, 2 * simulation.config.repairpersons,
                config["algorithm"], metadata.get("input"), metadata.get("pattern"),
                metadata.get("seed"), metadata.get("arrival_horizon"),
            ])
    #till here

    if any(simulation.trajectories.values()):
        with (output / "trajectories.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["server", "start_time", "end_time", "start_position", "end_position", "trip", "phase"])
            for server_id, legs in simulation.trajectories.items():
                writer.writerows([names[server_id], leg.t0, leg.t1, leg.x0, leg.x1, leg.trip, leg.phase]
                                 for leg in legs)
    return metrics


# Input: output is the results folder; simulation contains paths, requests, and service times.
def plot_run(output: Path, simulation: Simulation) -> None:
    # Input: the optional Matplotlib drawing library. Import its setup module.
    import matplotlib

    # Input: Matplotlib. Tell it to save image files instead of opening a graph window.
    matplotlib.use("Agg")

    # Input: Matplotlib's plotting tools. Give them the shorter name plt.
    import matplotlib.pyplot as plt
    # Input: Matplotlib tick-formatting tools. Lets us control how axis numbers appear.
    from matplotlib.ticker import FuncFormatter

    # Input: drawing-style settings. Remove the top and right border lines from plots.
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

    # Input: Matplotlib's built-in color set. Store colors for S1, S2, and later repairpersons.
    colors = plt.get_cmap("tab10")

    # Input: a vertical-axis number and its tick position. Formats y-axis labels.
    def hide_vertical_zero(value, tick_position):
        # Input: a y-axis value equal to zero. Hide it so only the x-axis shows 0 at the origin.
        if abs(value) < 1e-9:
            return ""

        # Input: any nonzero y-axis value. Return readable text such as 2, 3.5, or 10.
        return f"{value:g}"

    # Input: one new figure with one graph area. Create the repairperson trajectory plot.
    figure, axis = plt.subplots(figsize=(10, 5.5), constrained_layout=True)

    # Input: every repairperson stored in the simulation. Draw one movement path per repairperson.
    for server in simulation.servers:
        # Input: this repairperson's movement intervals. Store its path segments in legs.
        legs = simulation.trajectories[server.id]

        # Input: possibly empty movement intervals. Skip this repairperson if it has no recorded path.
        if not legs:
            # Input: no legs to draw. Continue to the next repairperson.
            continue

        # Input: each leg's start and end times. Build one continuous list of time values.
        times = [legs[0].t0] + [leg.t1 for leg in legs]

        # Input: each leg's start and end positions. Build one continuous list of position values.
        positions = [legs[0].x0] + [leg.x1 for leg in legs]

        # Input: time and position lists for this repairperson. Draw its colored movement path.
        axis.plot(times, positions, color=colors(server.id % 10),
                  linewidth=1.2, label=server.name, alpha=0.85)

    # Input: every completed request. Draw a gray waiting line from request arrival to service.
    for completion in simulation.completions:
        # Input: the request associated with this completion. Store it under a short name.
        request = completion.request

        # Input: request release time, service time, and fixed request position. Draw its waiting interval.
        axis.plot([request.release, completion.time], [request.position] * 2,
                  color="#9ca3af", linewidth=0.7, alpha=0.5)

    # Input: all request release times and positions. Draw black x marks where requests arrive.
    axis.scatter([item.request.release for item in simulation.completions],
                 [item.request.position for item in simulation.completions],
                 color="#111827", marker="x", s=20, label="Release", zorder=4, clip_on=False)

    # Input: all completion times and request positions. Draw hollow circles where requests are served.
    axis.scatter([item.time for item in simulation.completions],
                 [item.request.position for item in simulation.completions],
                 facecolors="white", edgecolors="#111827", s=22,
                 label="Service", zorder=5, clip_on=False)

    # Input: every completed request. Add its CSV ID beside the black release x marker.
    for item in simulation.completions:
        # Input: one completion record. Get the request containing its ID, release time, and position.
        request = item.request

        # Input: request ID and release coordinates. Draw a label such as R5 slightly above and right.
        axis.annotate(
            text=f"R{request.id}",
            xy=(request.release, request.position),
            xytext=(5, 6),
            textcoords="offset points",
            fontsize=8,
            color="#111827",
            ha="left",
            va="bottom",
            zorder=6,
        )

    # Input: the half-line endpoint L. Draw a light dashed line at the endpoint.
    axis.axhline(simulation.config.length, color="#cbd5e1", linewidth=0.8, linestyle="--")

    # Input: the physical interval [0, L]. Keep the vertical position axis inside that interval.
        # axis.set_ylim(0, simulation.config.length)

    # Input: the time axis. Start it exactly at time 0, where the two axes meet.
    axis.set_xlim(left=0)

    # Input: the physical half-line [0, L]. Start the position axis exactly at position 0.
    axis.set_ylim(bottom=0, top=simulation.config.length)

    # Input: the y-axis labels. Hide only its zero label to avoid showing two zeros at the origin.
    axis.yaxis.set_major_formatter(FuncFormatter(hide_vertical_zero))

    # Input: labels and title text. Describe the axes and this half-line simulation.
    axis.set(xlabel="Time (unit speed)",
             ylabel="Position on the half-line",
             title=f"Repairperson trajectories on [0, {simulation.config.length:g}], "
                   f"with m={simulation.config.repairpersons}")

    # Input: all plotted repairperson and request labels. Show a legend near the top-left.
    axis.legend(ncol=min(6, simulation.config.repairpersons + 2), fontsize=8, loc="upper left")

    # Input: the trajectory graph. Add a light background grid to make values easier to read.
    axis.grid(alpha=0.15)

    # Input: the results folder. Save the first plot as trajectories.png.
    figure.savefig(output / "trajectories.png", dpi=180)

    # Input: the completed trajectory figure. Close it to free memory.
    plt.close(figure)

    # Input: one new figure with one graph area. Create the request-ratio plot.
    figure, axis = plt.subplots(figsize=(10, 4.5), constrained_layout=True)

    # # Input: all completions. Keep only requests whose lower bound is greater than zero.
    # valid = [item for item in simulation.completions if item.request.lower_bound > 0]

    # # Input: valid request release times and ratios. Draw one blue dot per request.
    # axis.scatter([item.request.release for item in valid],
    #              [item.time / item.request.lower_bound for item in valid],
    #              s=30, color="#2563eb", label="Request ratio")

    # # Input: simulation measurements. Get the paper's theoretical bound for this m value.
    # metrics = simulation.metrics()

    # # Input: the theoretical paper bound. Draw it as a red dashed horizontal line.
    # axis.axhline(metrics["paper_claimed_halfline_bound"], linestyle="--", color="#dc2626",
    #              label="Manuscript claimed bound")

    # Input: all completed requests. Keep only requests whose lower bound is greater than zero.
    valid = [item for item in simulation.completions if item.request.lower_bound > 0]

    # Input: valid requests. Collect every different release time for an x-axis tick.
    release_times = sorted({item.request.release for item in valid})

    # Input: valid request release times and ratios. Draw one blue dot for each request.
    axis.scatter([item.request.release for item in valid],
                 [item.time / item.request.lower_bound for item in valid],
                 s=30, color="#2563eb", label="Request ratio")

    # Input: every request with a nonzero lower bound. Add its CSV ID beside its blue ratio dot.
    for item in valid:
        # Input: one completion record. Get the original request information.
        request = item.request

        # Input: completion time and lower bound. Calculate this request's plotted ratio value.
        ratio = item.time / request.lower_bound

        # Input: request ID, release time, and ratio. Draw a label such as R5 beside the blue dot.
        axis.annotate(
            text=f"R{request.id}",
            xy=(request.release, ratio),
            xytext=(5, 6),
            textcoords="offset points",
            fontsize=8,
            color="#111827",
            ha="left",
            va="bottom",
            zorder=6,
        )

    # Input: simulation measurements. Get the paper's theoretical bound for this value of m.
    metrics = simulation.metrics()

    # Input: the numerical paper bound. Store it so we can draw and label the red line.
    bound = metrics["paper_claimed_halfline_bound"]

    # Input: the claimed bound. Draw the red dashed horizontal bound line.
    axis.axhline(bound, linestyle="--", color="#dc2626", label="Claimed bound")

    # Input: the horizontal time axis. Start it exactly at release time 0.
    axis.set_xlim(left=0)

    # Input: the vertical ratio axis. Start it exactly at ratio 0.
    axis.set_ylim(bottom=0)

    # Input: the actual release times in this input. Show one x-axis value for each release time.
    axis.set_xticks(release_times)

    # Input: release-time numbers. Display them cleanly, such as 0, 1, 2, 3, 5, 7, 10, and 12.
    axis.set_xticklabels([f"{release_time:g}" for release_time in release_times])

    # Input: Matplotlib's normal y-axis ticks. Store them before adding the exact claimed-bound tick.
    ratio_ticks = list(axis.get_yticks())

    # Input: the current tick values and claimed bound. Add the bound only if it is not already present.
    if not any(abs(tick - bound) < 1e-9 for tick in ratio_ticks):
        ratio_ticks.append(bound)

    # Input: normal ticks plus the claimed bound. Sort and place them on the y-axis.
    axis.set_yticks(sorted(ratio_ticks))

    # Input: a y-axis tick value and its position. Format ordinary ticks and the special bound tick.
    def format_ratio_tick(value, tick_position):
        # Input: a y-axis value equal to zero. Hide it so the x-axis supplies the single origin 0.
        if abs(value) < 1e-9:
            return ""

        # Input: the claimed-bound value. Show it to six decimal places, such as 3.732051.
        if abs(value - bound) < 1e-9:
            return f"{bound:.6f}"

        # Input: any ordinary nonzero tick. Return readable text such as 1, 2, or 3.5.
        return f"{value:g}"

    # Input: the ratio-axis tick formatter. Apply the custom labels, including the exact bound value.
    axis.yaxis.set_major_formatter(FuncFormatter(format_ratio_tick))

    # Input: labels and title text. Explain that the blue dots are individual request ratios.
    axis.set(xlabel="Release time",
             ylabel="C / max(release, distance)",
             title="Per-request ratios to individual lower bounds")

    # Input: the ratio graph. Add a light background grid to make values easier to read.
    axis.grid(alpha=0.15)

    # Input: ratio-plot labels. Show the legend.
    axis.legend(fontsize=9)

    # Input: the results folder. Save the second plot as request_ratios.png.
    figure.savefig(output / "request_ratios.png", dpi=180)

    # Input: the completed ratio figure. Close it to free memory.
    plt.close(figure)


def print_metrics(metrics: dict) -> None:
    print(f"Half-line [0, {metrics['length']:g}] | m={metrics['repairpersons']} | requests={metrics['requests']}")
    print(f"Corresponding equal-split full-line k={metrics['corresponding_even_full_line_k']} (context only).")
    print("Continuous patrol from time zero; time-preserving waiting at the endpoint.")
    fields = [
        ("Sum of completion times", "total_completion_time"),
        ("Mean completion time", "mean_completion_time"),
        ("Mean flow time (C-release)", "mean_flow_time"),
        ("Makespan (last completion)", "makespan"),
        ("Sum of individual lower bounds", "sum_individual_lower_bounds"),
        ("Online / lower bound (not exact OPT)", "online_over_lower_bound"),
        ("Maximum per-request / lower bound", "max_request_over_lower_bound"),
        ("Exact offline optimum", "offline_optimum"),
        ("Empirical online / exact OPT", "empirical_ratio_to_optimum"),
    ]
    for label, key in fields:
        value = metrics.get(key)
        print(f"  {label:42s} {'n/a' if value is None else f'{value:.6f}'}")
    print(f"Offline status: {metrics['offline_status']}")

    # Input: the number of repairpersons on this one half-line. Store it in the shorter name m.
    m = metrics["repairpersons"]

    # Input: the equal-split full-line interpretation. Two half-lines with m repairpersons give k = 2*m.
    k = 2 * m

    # Input: the bound already calculated by halfline_trp.py. Store it under a readable name.
    bound = metrics["paper_claimed_halfline_bound"]

    # Input: m. Use the paper's separate formula when one repairperson works on the half-line.
    if m == 1:
        # Input: the m=1 case. Store the paper's k=2 formula as display text.
        formula = "2 + sqrt(3)"

    # Input: m greater than 1. Use Algorithm 2's paper formula as display text.
    else:
        # Input: k and m. Build readable text for max{1 + 8/(5 floor(k/2) - 3), 2}.
        formula = f"max(1 + 8/(5*floor({k}/2) - 3), 2)"

    # Input: k, formula text, and the numerical bound. Print the theoretical upper bound from the paper.
    print(f"Theoretical competitive-ratio bound for k={k}: {formula} = {bound:.6f}.")

    # Input: whether all release times are integers. Check whether the paper-bound comparison applies.
    if metrics["paper_bound_check_applicable"]:
        # Input: the true/false result of the bound check. Create a readable status message.
        status = "VIOLATION OBSERVED: inspect this input" if metrics["observed_bound_violation"] else "no violation observed on this input."

        # Input: the status text. Print the result of checking this particular request set.
        print(f"Check on this input: {status}")

    # Input: a run containing noninteger release times. Explain why the theorem comparison is only informational.
    else:
        # Input: the noninteger-release situation. Print that the theoretical bound was not checked.
        print("The bound is shown for reference only because this run uses noninteger release times.")
    # if metrics["paper_bound_check_applicable"]:
    #     status = "VIOLATION OBSERVED: inspect this input" if metrics["observed_bound_violation"] else "no violation observed on this input"
    #     print(f"Manuscript bound {metrics['paper_claimed_halfline_bound']:.6f}: {status}.")
    # else:
    #     print("Manuscript bound is reference only for noninteger releases.")
    print("A finite experiment does not establish a worst-case competitive ratio.")




def plot_request_timeline(output, simulation):
    """Save one row per request from release time to completion time."""
    items = sorted(simulation.completions, key=lambda item: item.request.id)
    figure, axis = plt.subplots(figsize=(10, max(3, len(items) * 0.32)))
    for row, item in enumerate(items):
        request = item.request
        axis.hlines(row, request.release, item.time, color="#6b7280", linewidth=3,
                    label="Flow time" if row == 0 else "")
        axis.scatter(request.release, row, marker="x", color="#111827", zorder=3,
                     label="Release" if row == 0 else "")
        axis.scatter(item.time, row, facecolors="white", edgecolors="#111827", zorder=3,
                     label="Completion" if row == 0 else "")
    axis.set_yticks(range(len(items)), labels=[f"R{item.request.id}" for item in items])
    axis.set(xlabel="Time", ylabel="Request", title="Request timeline: release to completion")
    axis.set_xlim(left=0)
    axis.invert_yaxis()
    axis.legend()
    figure.tight_layout()
    figure.savefig(output / "request_timeline.png", dpi=200)
    plt.close(figure)


def plot_request_ratio_bars(output, simulation):
    """Save one completion-to-lower-bound ratio bar per valid request."""
    items = [item for item in simulation.completions if item.request.lower_bound > 0]
    items.sort(key=lambda item: item.request.id)
    labels = [f"R{item.request.id}" for item in items]
    ratios = [item.time / item.request.lower_bound for item in items]
    metrics = simulation.metrics()
    figure, axis = plt.subplots(figsize=(max(8, len(items) * 0.18), 5))
    axis.bar(labels, ratios, color="#2563eb", label="Request ratio")
    if metrics.get("paper_bound_check_applicable"):
        axis.axhline(metrics["paper_claimed_halfline_bound"], color="#dc2626",
                     linestyle="--", label="Claimed bound")
    axis.set(xlabel="Request ID", ylabel="C / max(release, distance)",
             title="Per-request ratios to individual lower bounds")
    axis.set_ylim(bottom=0)
    axis.tick_params(axis="x", labelrotation=90)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output / "request_ratio_bars.png", dpi=200)
    plt.close(figure)
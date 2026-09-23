# First lesson: a simpler starting file for the existing half-line TRP package.
# Run this file with: python run_beginner.py
# Keep it beside halfline_trp.py, workloads.py, offline.py, and reporting.py.
# A comment explains the input and action of every nonblank Python code line.
# Blank lines separate ideas; Python ignores comments and blank lines.

# Input: the pathlib module included with Python. Makes Path available for file and folder names.
from pathlib import Path
from platform import python_version
# Input: the local halfline_trp.py file. Imports the settings container and simulation function.
from halfline_trp import Config, simulate
# Input: the local workloads.py file. Imports functions for generating requests or reading a CSV.
from workloads import generate_requests, read_requests
# Input: the local offline.py file. Imports the function that finds the exact small-input benchmark.
from offline import exact_offline
# Input: the local reporting.py file. Imports functions for saving, printing, and plotting results.
from reporting import write_run, print_metrics, plot_run, plot_request_timeline, plot_request_ratio_bars

# CHANGE THESE SETTINGS BEFORE RUNNING THE FILE.

# Input: a positive number. Sets the endpoint; 10 means the physical interval [0, 10].
# length = 10
length = 100
# Input: a whole number of at least 1. Sets how many repairpersons work on this one half-line.
repairpersons = 3
# Input: a whole number of at least 0. Sets the request count when generating requests.
# request_count = 8
request_count = 1000000
# Input: a whole number of at least 0. Sets the last possible generated integer release time starting from 0
arrival_horizon = 100
# Input: a pattern name as text. Selects uniform positions and releases for generated requests.
pattern = "uniform"
# pattern = "half_grid" #this creates requests like at 0, 0.5, 1.0, 1.5, ... up to length
# Input: a whole number. Makes generated requests repeatable when all generation settings match.
seed = 19
# Input: a CSV filename as text, or "". A filename reads that file; "" generates requests instead.
# input_csv = "examples/requests.csv"
input_csv = ""
# Input: "auto", "exact", or "none". Chooses automatic, required, or disabled offline optimization.
offline_mode = "auto"
# Input: a whole number of at least 1. Limits the costly offline search; 10 is the recommended default.
exact_limit = 10
# Input: True or False, Python's yes/no values. Chooses whether to record repairperson paths.
# save_trajectories = True
save_trajectories = False
# Input: True or False. Chooses whether to draw a figure; True requires Matplotlib and recorded paths.
# make_plot = True
make_plot = False
# Input: a folder name as text. Sets where this run saves its output files.
# output_folder = "results/beginner_m2"
# output_folder = "results/uniform_L10000_m6_n10000000_seed9"
output_folder = f"results/paper_L100_m3/seed_{seed}"


# CHECK THE SETTINGS THAT CONTROL THIS STARTING FILE.

# Input: offline_mode as text. Checks whether it is missing from the three allowed choices.
if offline_mode not in ["auto", "exact", "none"]:
    # Input: an invalid offline_mode. Stops execution and explains the allowed choices.
    raise ValueError("offline_mode must be 'auto', 'exact', or 'none'.")
# Input: exact_limit as a whole number. Checks whether the search limit is below 1.
if exact_limit < 1:
    # Input: a search limit below 1. Stops execution with an explanation.
    raise ValueError("exact_limit must be at least 1.")
# Input: the two True/False settings. Checks whether plotting was requested without recorded paths.
if make_plot and not save_trajectories:
    # Input: that incompatible setting combination. Stops execution and explains the correction.
    raise ValueError("Set save_trajectories = True when make_plot = True.")

# BUILD THE REQUESTS AND RUN THE REPAIRPERSON PATROLS.

# Input: length and repairpersons. Validates them and stores them together in a settings object.
config = Config(length=length, repairpersons=repairpersons)
# Input: input_csv as text. Chooses generation when the filename is the empty string "".
if input_csv == "":
    # Input: the five generation settings. Produces a list containing request_count request records.
    requests = generate_requests(request_count, length, arrival_horizon, seed, pattern)
    # Input: the actual generation settings. Records them in a dictionary, which stores named values.
    experiment = {"input": "generated", "pattern": pattern, "seed": seed, "arrival_horizon": arrival_horizon}
# Input: a nonempty input_csv filename. Chooses the file-reading branch instead of generation.
else:
    # Input: a readable CSV with id, release_time, and position columns. Produces a list of requests.
    requests = read_requests(input_csv)
    # Input: the CSV filename. Records the source; None means the generation settings were not used.
    experiment = {"input": input_csv, "pattern": None, "seed": None, "arrival_horizon": None}
# Input: the request list, settings object, and path-recording choice. Calculates services and paths.
simulation = simulate(requests, config, record_trajectories=save_trajectories)

# DECIDE WHETHER TO COMPUTE THE BEST OFFLINE COST.

# Input: no computed benchmark yet. Uses None to represent an absent offline result.
offline = None
# Input: no optimization requested yet. Sets the starting explanation for the benchmark status.
offline_status = "disabled"
# Input: no optimization decision yet. Starts with False, meaning do not run the expensive search.
solve_offline = False
# Input: offline_mode as text. Checks whether exact optimization was explicitly requested.
if offline_mode == "exact":
    # Input: the exact-mode choice. Requests optimization; the solver will enforce its limits.
    solve_offline = True
# Input: a mode that was not "exact". Checks whether automatic selection was requested.
elif offline_mode == "auto":
    # Input: the request list and two count settings. Allows small searches or a dedicated server per request.
    if len(requests) <= exact_limit or repairpersons >= len(requests):
        # Input: an input selected by the automatic rule. Turns on offline optimization.
        solve_offline = True
    # Input: an automatic-mode input too large for either rule. Chooses to skip offline optimization.
    else:
        # Input: exact_limit as a number. Inserts it into text explaining why OPT was not computed.
        offline_status = f"not computed: n exceeds exact limit {exact_limit}"
# Input: solve_offline as True or False. Runs the next two lines only when it is True.
if solve_offline:
    # Input: the same requests, settings, and search limit. Finds the optimal cost and server routes.
    offline = exact_offline(requests, config, max_requests=exact_limit)
    # Input: a successful offline computation. Records that decimal calculations use floating-point numbers.
    offline_status = "exact (floating-point arithmetic)"

# SAVE AND DISPLAY THE RESULTS.

# Input: experiment as a dictionary and exact_limit as a number. Adds the search limit to the run record.
experiment["exact_limit"] = exact_limit
# Input: the current Python installation. Adds its version number as text to the run record.
experiment["python"] = python_version()
# Input: save_trajectories as True or False. Records whether paths were requested.
experiment["trajectory_recording"] = save_trajectories
# Input: output_folder as text. Converts the folder name into the Path type expected by the writer.
output = Path(output_folder)
# Input: the folder, simulation, optional benchmark, status, and run record. Saves files and returns metrics.
metrics = write_run(output, simulation, offline, offline_status, experiment)
# Input: metrics, a dictionary of measured values. Prints their labels and values in the terminal.
print_metrics(metrics)
# Input: make_plot as True or False. Draws a figure only when the setting is True.
if make_plot:
    # Input: the output folder and recorded simulation. Saves trajectories.png using optional Matplotlib.
    plot_run(output, simulation)
    plot_request_timeline(output, simulation)  # Saves the request timeline plot.
    plot_request_ratio_bars(output, simulation)  # Saves the ratio bar-chart plot.
# Input: the output Path. Prints its complete location so you can find the saved files.
print("Outputs:", output.resolve())

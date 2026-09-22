# Your first Python lesson: starting a half-line TRP simulation

## What this program does

Imagine a road that begins at 0 and ends at L. A request means that someone
at a particular position needs a repair at a particular time. Several
repairpersons start at 0 and follow the movement rules from your paper.

The program calculates when each request gets served. It then adds those
service times and reports other measurements, such as how long requests
waited after arriving. For small inputs it also calculates the best possible
total service time if the repairpersons knew every request in advance. This
gives you a benchmark for the online algorithm.

The primary objective is the sum of absolute service times, measured from
time zero. Waiting time after release is another measurement. For example,
a request released at time 10 and served at time 14 contributes 14 to the
primary objective and has a waiting time of 4.

I am assuming this is the half-line package from our preceding exchange.
This first lesson simplifies its starting file, `run_simulation.py`. A starting
file, also called an entry point, is the file you run to begin the program.
It is the best place to learn the overall sequence before studying the
movement formulas or optimization code.

## How the files fit together

| File | Its job in plain language |
|---|---|
| `run_beginner.py` | The new, fully commented starting file for this lesson |
| `run_simulation.py` | The original starting file, controlled by terminal options |
| `workloads.py` | Makes a list of requests or reads one from a CSV file |
| `halfline_trp.py` | Applies the repairperson movement rules and calculates service times |
| `offline.py` | Finds the best possible cost with advance knowledge for manageable inputs |
| `reporting.py` | Saves measurements and optionally draws a figure |
| `run_experiments.py` | Repeats simulations across seeds and repairperson counts |
| `audit_bounds.py` | Checks many selected requests against the paper's stated bounds |

The new starting file uses the same calculation files. It connects them in
this order: settings, requests, simulation, optional benchmark, saved results.
The experiment and audit scripts are not needed for your first run.

This is a simplification of the entry file, not a claim that every file in
the research package has been rewritten. Every nonblank code line in
`run_beginner.py` has a comment describing its input and action. The original
calculation modules remain available for later lessons.

## What became simpler

In the original file, a library named `argparse` reads options such as
`--length 10` from your terminal. That is convenient for repeated experiments,
but adds code you do not need to learn for your first simulation.

In the beginner version, you edit clearly named settings at the top of the
file. Execution then proceeds straight down the page. There are no custom
function definitions, compact one-line conditional expressions, or command-line
argument setup to follow in this starting file.

Some choices take several ordinary `if` and `else` lines. That can be easier
to read than squeezing the same decision into one complicated expression.
Explanatory comments make the file longer on the screen; the working Python
portion has 54 nonblank code lines.

The input methods, request patterns, exact/auto/none benchmark modes, optional
trajectory recording, and optional plotting are retained as editable settings.
The default settings select the included eight-request example, with three
repairpersons on [0,10]. The original command-line file's defaults instead
generate 100 requests on [0,100]; select matching settings when comparing runs.

The new runner was compared with the original on seven cases: the included
example, two repairpersons, generated requests with exact OPT, a 100-request
automatic run without recorded paths, one repairperson per request, a disabled
benchmark, and an empty stream. All JSON and CSV values matched. Numeric text
such as `10` and `10.0` was compared as the same number. A separate check
confirmed that all 54 code lines have an input-and-action comment.

## Run it once before changing anything

Use Python 3.10 or newer. Extract the updated package. Open a terminal inside
its `halfline_trp` folder and run:

```bash
python run_beginner.py
```

If your system calls Python `python3`, use `python3 run_beginner.py` instead.
The file must stay beside the other Python files. It is not a standalone
replacement for the entire package.

The default input is `examples/requests.csv`. After running, look in
`results/beginner_run` for these files:

| Output | How to use it |
|---|---|
| `requests.csv` | Inspect the exact request positions and release times |
| `completions.csv` | Inspect when each request was served and how long it waited |
| `summary.json` | See settings, total costs, and the benchmark in a structured text file |
| `trajectories.csv` | Inspect the repairpersons' movement and waiting intervals |

The terminal should report approximately:

| Measurement | Default example result |
|---|---:|
| Online sum of completion times | 54.733333 |
| Exact offline optimum | 42.000000 |
| Online / exact OPT | 1.303175 |

For this input, the online total is about 30.3% above the best possible total.
This is a measurement for these eight requests, not a proof about all inputs.

## Read the starting file in five steps

### 1. Imports make existing tools available

A line beginning with `from ... import ...` makes a named tool available to
this file. It does not install software or download anything.

For example, importing `generate_requests` allows this file to ask the
existing request-generation code to make requests. You can first understand
what goes into that function and what comes back, then study its internal
steps later.

`Path` and `python_version` come with Python. The other imported tools are in
the adjacent project files. Matplotlib is needed only when you request a plot.

### 2. Settings give names to your choices

The symbol `=` stores a value under a name. In `length = 10`, the value 10
is stored under the name `length` so later lines can use it.

| Setting | Kind of value | Meaning |
|---|---|---|
| `length` | Positive number | Distance from zero to the endpoint |
| `repairpersons` | Whole number at least 1 | Number actually working on this half-line |
| `request_count` | Whole number at least 0 | Number to generate |
| `arrival_horizon` | Whole number at least 0 | Last possible generated release time |
| `pattern` | Text in quotation marks | Which request distribution to use |
| `seed` | Whole number | Makes generated inputs repeatable |
| `input_csv` | Filename in quotes, or `""` | Read a file, or generate requests if empty |
| `offline_mode` | `"auto"`, `"exact"`, or `"none"` | How to select the offline benchmark |
| `exact_limit` | Whole number at least 1 | Default request limit for the costly search |
| `save_trajectories` | `True` or `False` | Whether to record paths |
| `make_plot` | `True` or `False` | Whether to draw the recorded paths |
| `output_folder` | Folder name in quotes | Where to put this run's results |

`True` and `False` begin with capital letters and have no quotation marks.
They are Python's two yes/no values. `"False"`, with quotation marks, is text
and does not mean the same thing.

### 3. Requests come from exactly one source

When `input_csv` contains a filename, that CSV controls the requests.
`request_count`, `arrival_horizon`, `pattern`, and `seed` are then unused.
This explains why changing `request_count` alone does not change the default
eight-request example.

To generate 100 requests instead, edit these lines at the top of the file:

```python
# Input: an empty text value. Selects generated requests instead of CSV input.
input_csv = ""
# Input: a positive number. Sets the domain to [0, 100].
length = 100
# Input: a whole number. Requests 100 generated requests on that half-line.
request_count = 100
# Input: a whole number. Uses two repairpersons on this one half-line.
repairpersons = 2
# Input: an allowed pattern name. Concentrates requests near zero.
pattern = "near_origin"
# Input: a folder name as text. Keeps this experiment's output in a separate folder.
output_folder = "results/near_origin"
```

Leave `arrival_horizon = 100` to allow generated releases at integer times
from 0 through 100. This is the last possible arrival time, not a cutoff for
serving requests.

Allowed patterns are `uniform`, `early`, `bursty`, `near_origin`,
`near_endpoint`, `endpoints`, and `hotspots`. To create exactly the same
generated input again, retain all generation settings, including the seed.

### 4. The simulation and benchmark do different jobs

`simulate(...)` applies the online patrols to the requests. A function is a
named set of instructions; calling it means asking Python to carry out those
instructions using the supplied values.

`Config(...)` groups the endpoint and repairperson count together. You can
think of this object as a settings record. The `simulation` object returned
by `simulate(...)` is another record, holding the calculated services and paths.

`exact_offline(...)` solves a different problem: how well could repairpersons
do if they knew every request in advance? They still have the same starting
position, speed limit, endpoint, and number of repairpersons.

Automatic mode attempts exact optimization for at most `exact_limit` requests. It also
handles the easy case with at least one repairperson per request. Otherwise
it skips the expensive search and says that OPT was not computed. Exact mode
requires a solution and raises an error if the input or internal search budget
is too large. None mode skips the benchmark entirely.

The exact optimization cannot be replaced by adding each request's individual
best service time: a small number of repairpersons may not be able to attain
all those times together. Replacing it with the nearest-request rule would
also change the benchmark. The existing optimizer remains necessary to retain
the original exact results and practical small-input search behavior; it can
be explained separately. No extra library is required for that solver.

### 5. The writer saves what happened

`experiment` is a dictionary: a collection of named values, such as
`"seed"` and its chosen number. These values explain how the run was set up.

`write_run(...)` saves the inputs and results, and returns another dictionary
called `metrics`. `print_metrics(metrics)` displays the measurements.

If `make_plot` is True, `plot_run(...)` creates `trajectories.png`. To enable it,
first install the optional drawing library:

```bash
python -m pip install matplotlib
```

Then set both `make_plot` and `save_trajectories` to `True`. The drawing library
is optional; it is not needed to simulate requests, compute OPT, or save CSVs.

## Small Python symbols you will meet

| Symbol or word | Meaning here |
|---|---|
| `#` | Starts a comment; Python ignores the rest of that line |
| `=` | Stores a value |
| `==` | Checks whether two values are equal |
| `if` | Runs an indented block only when a condition is true |
| `elif` | Checks another condition when the preceding branch did not run |
| `else` | Runs the alternative block |
| `and`, `or`, `not` | Combines or reverses yes/no conditions |
| `None` | Represents an absent result or an unused setting |
| `len(requests)` | Counts the requests in the list |
| `experiment["seed"]` | Selects the value named `"seed"` in the dictionary |
| `f"...{exact_limit}..."` | Builds text by inserting the variable's value |
| `raise ValueError(...)` | Stops execution because an input is unsuitable |

Indentation is meaningful in Python. The indented lines beneath an `if`
belong to that condition. Keep their spaces when editing the file. Comments
do not run, so changing only a comment does not change the simulation.

## What the simplification changes, and what to watch for

This is an editable-settings entry point. It does not accept the original
terminal options such as `--length` or `--requests`. Use `run_simulation.py`
when you want those options. Run `run_beginner.py` directly; importing it from
another Python file would also execute its top-to-bottom instructions.

Input problems produce Python error messages with the reason near the end.
The original command-line runner wraps some of those errors in shorter messages;
the beginner file omits that extra error-handling structure. Examples:

- A missing CSV usually means you are outside the `halfline_trp` folder or
  misspelled the filename.
- A request beyond `length` means the chosen endpoint is too short for that CSV.
- A missing Matplotlib error means plotting was enabled before installing it.
- An exact-search limit error means the requested benchmark is too costly for
  the configured input/search limits.

Use a different output folder when changing experiments. Reusing a folder
overwrites files with matching names, and older optional plot or trajectory
files can remain if the next run does not produce them.

For this paper's model, retain integer release times when generating or
constructing theorem-related inputs. The original code allows fractional CSV
releases for exploration but marks the manuscript bound comparison inapplicable.
The time-preserving endpoint waiting and continuous patrol conventions also
remain the ones confirmed in our preceding exchange.

## A useful first exercise

Run the unchanged eight-request example. Then change only `repairpersons`
from 3 to 2 and `output_folder` to `"results/beginner_m2"`. Run it again.
The online completion sum should become approximately 59.642857. The exact
offline optimum remains 42 for this particular example, so Online/OPT becomes
approximately 1.420068.

This exercise changes one scientific input while keeping the requests fixed.
After understanding the entry file, `workloads.py` is a natural next lesson:
it introduces lists, loops, request generation, and CSV reading using smaller
pieces of code than the movement engine or exact optimizer.

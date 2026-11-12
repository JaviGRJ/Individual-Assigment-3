# Assignment 3 — Parallel Matrix Multiplication

## Description

This project compares a sequential dense matrix multiplication with a threaded
implementation.

- `methods.py`: sequential and parallel multiplication plus correctness tests.
- `benchmark_assignment3.py`: data generation, benchmarking and speedup
  calculations.
- `generate_graphics.py`: generates the runtime, speedup and memory figures.
- `results.csv`: raw measurements.
- `summary.csv`: medians, IQR, memory, speedup and efficiency.
- `environment.json`: experiment and environment configuration.
- `runtime.svg`: runtime figure.
- `speedup.svg`: speedup figure.
- `memory.svg`: memory figure.
- `REPORT.md`: report source.
- `Assignment03_Javier_Guerra_Report.pdf`: final report.

The sequential baseline extends the validated dense implementation from
Assignments 1 and 2. The parallel implementation uses Python's
`ThreadPoolExecutor`.

## Execution

Run the following commands from the `assignment-3` directory:

```powershell
python methods.py
python benchmark_assignment3.py
python generate_graphics.py
```

The first command runs the correctness tests.

The second command generates the inputs, validates both implementations,
performs the measurements and creates the CSV and JSON files.

The third command creates the SVG figures.

## Experiment

The tested matrix sizes are:

```text
32, 64, 96, 128
```

The tested parallel configurations use:

```text
1, 2, 4 and 8 worker threads
```

The experiment uses:

- random seed `20261112`;
- Python `float` values;
- one warm-up;
- five measured repetitions;
- a 60-second time limit;
- a 2048 MiB memory limit.

The same input matrices are used by the sequential and parallel methods for
each matrix size.

Each parallel worker calculates complete output rows. Workers therefore do not
write to the same output elements.

## Measurements

The timed region includes only the multiplication call. Input generation,
allocation, validation and output writing are outside the timed region.

The reported central measure is the median. Variability is reported using the
inclusive interquartile range.

Speedup and efficiency are calculated as:

```text
speedup = sequential median time / parallel median time
efficiency = speedup / thread count
```

Memory is measured as peak Python allocation using `tracemalloc`. This is not
the complete operating-system process memory.

The benchmark records the physical-core count, logical-processor count,
requested thread count, affinity setting and internal numerical-library thread
count in `environment.json`.

## Correctness

Every parallel result is compared with the sequential result using absolute and
relative tolerance `1e-12`.

The one-thread parallel configuration is included to measure thread-pool
overhead.

This implementation does not include vectorisation.

## Outputs

The benchmark creates:

```text
results.csv
summary.csv
environment.json
```

The figure script creates:

```text
runtime.svg
speedup.svg
memory.svg
```

`results.csv` contains the individual measurements. `summary.csv` contains
the median, IQR, memory, speedup, efficiency, sample count and status for each
configuration.

## Reproducibility

From the assignment directory, run:

```powershell
python methods.py
python benchmark_assignment3.py
python generate_graphics.py
```

The benchmark regenerates the matrices from the fixed seed and records the
configuration used for the experiment.

The sequential baseline is carried forward from the validated matrix
multiplication work in Assignments 1 and 2.

## Limitation

The parallel implementation uses CPython threads. CPU-bound Python code can be
limited by the Global Interpreter Lock, and creating and coordinating workers
adds overhead. The results therefore describe this Python implementation and
environment, not all possible parallel matrix multiplication implementations.

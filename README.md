# Assignment 3 — Parallel Matrix Multiplication

## Description

This project compares:

- a sequential dense baseline;
- the same multiplication using 1, 2, 4 and 8 Python worker threads;
- an optional NumPy vectorized multiplication, measured separately.

Files:

- `methods.py`: sequential and threaded methods and tests.
- `vectorized.py`: NumPy `matmul` method and test.
- `benchmark_assignment3.py`: benchmark and result generation.
- `generate_graphics.py`: runtime, speedup and memory figures.
- `requirements.txt`: NumPy dependency.
- `results.csv`, `summary.csv`, `environment.json`: measurements and metadata.
- `runtime.svg`, `speedup.svg`, `memory.svg`: figures.
- `REPORT.md` and `Assignment03_Javier_Guerra_Report.pdf`: report.

## Requirements and execution

Python 3.10 or later is required. Install the optional vectorization
dependency:

```powershell
python -m pip install -r requirements.txt
```

Run from this directory:

```powershell
python methods.py
python vectorized.py
python benchmark_assignment3.py
python generate_graphics.py
```

The benchmark uses sizes `32, 64, 96, 128`, thread counts `1, 2, 4, 8`,
five repetitions and one warm-up. The same matrices are used by all methods.
Each worker calculates complete output rows, so workers do not write to the
same output elements.

The timer surrounds only multiplication. Input generation, allocation,
validation and file output are excluded. Results report median and inclusive
IQR. Speedup is `Tseq / Tp` and efficiency is `speedup / p`.

The optional vectorized method uses NumPy `matmul` with one controlled backend
thread. The benchmark sets `OMP_NUM_THREADS`, `MKL_NUM_THREADS` and
`OPENBLAS_NUM_THREADS` to `1`. NumPy backend information is recorded, but no
disassembly is performed; the result is therefore reported as vectorized
library performance, not proof of a particular SIMD instruction.

Memory is peak Python allocation from `tracemalloc`, not total process memory.
The limits are 60 seconds and 2048 MiB per configuration. The complete
configuration, hardware and thread settings are in `environment.json`.

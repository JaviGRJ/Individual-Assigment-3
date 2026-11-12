
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

from methods import Matrix, assert_close, multiply_parallel, multiply_sequential
from vectorized import multiply_vectorized

ROOT = Path(__file__).resolve().parent
DEFAULT_SIZES = [32, 64, 96, 128]
DEFAULT_THREADS = [1, 2, 4, 8]
SEED = 20261112
REPETITIONS = 5
WARMUPS = 1
TIME_LIMIT_SECONDS = 60.0
MEMORY_LIMIT_MIB = 2048.0


def make_matrix(rng: random.Random, n: int) -> Matrix:
    return [[float(rng.randint(-8, 8)) for _ in range(n)] for _ in range(n)]


def calculate_iqr(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return quartiles[2] - quartiles[0]


def physical_core_count() -> int | None:
    if os.name != "nt":
        return None
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "(Get-CimInstance Win32_Processor | "
            "Measure-Object -Property NumberOfCores -Sum).Sum",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    value = result.stdout.strip()
    return int(value) if value.isdigit() else None


def measure(method, arguments: tuple, expected: Matrix) -> tuple[list[float], float, str]:
    for _ in range(WARMUPS):
        assert_close(method(*arguments), expected)

    tracemalloc.reset_peak()
    samples: list[float] = []
    started = time.perf_counter()
    status = "ok"

    for _ in range(REPETITIONS):
        sample_started = time.perf_counter()
        result = method(*arguments)
        elapsed_ms = (time.perf_counter() - sample_started) * 1000.0
        assert_close(result, expected)
        samples.append(elapsed_ms)
        if time.perf_counter() - started > TIME_LIMIT_SECONDS:
            status = "timeout"
            break

    peak_mib = tracemalloc.get_traced_memory()[1] / (1024 * 1024)
    if peak_mib > MEMORY_LIMIT_MIB:
        status = "memory_limit"
    return samples, peak_mib, status


def write_raw(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "size", "method", "variant", "threads", "internal_threads",
        "repetition", "time_ms", "peak_memory_mib", "status",
        "speedup", "efficiency",
    ]
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path: Path, rows: list[dict[str, object]]) -> None:
    grouped: dict[tuple[str, str, str, str], list[dict[str, object]]] = {}
    for row in rows:
        key = (
            str(row["size"]),
            str(row["method"]),
            str(row["variant"]),
            str(row["threads"]),
        )
        grouped.setdefault(key, []).append(row)

    fields = [
        "size", "method", "variant", "threads", "internal_threads",
        "median_ms", "iqr_ms", "peak_memory_mib", "samples", "status",
        "speedup", "efficiency",
    ]
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for key, group in grouped.items():
            values = [
                float(row["time_ms"])
                for row in group
                if row["status"] == "ok"
            ]
            writer.writerow(
                {
                    "size": key[0],
                    "method": key[1],
                    "variant": key[2],
                    "threads": key[3],
                    "internal_threads": group[-1]["internal_threads"],
                    "median_ms": f"{statistics.median(values):.6f}" if values else "",
                    "iqr_ms": f"{calculate_iqr(values):.6f}" if values else "",
                    "peak_memory_mib": group[-1]["peak_memory_mib"],
                    "samples": f"{len(values)}/{len(group)}",
                    "status": group[-1]["status"],
                    "speedup": group[-1].get("speedup", ""),
                    "efficiency": group[-1].get("efficiency", ""),
                }
            )


def add_pending(
    pending: list[tuple],
    n: int,
    method: str,
    variant: str,
    threads: int,
    internal_threads: int,
    samples: list[float],
    memory: float,
    status: str,
) -> None:
    pending.append((
        n, method, variant, threads, internal_threads,
        samples, memory, status,
    ))


def run(sizes: list[int], thread_counts: list[int]) -> dict[str, int]:
    rng = random.Random(SEED)
    pending: list[tuple] = []

    for n in sizes:
        a = make_matrix(rng, n)
        b = make_matrix(rng, n)
        expected = multiply_sequential(a, b)

        samples, memory, status = measure(
            multiply_sequential, (a, b), expected
        )
        add_pending(pending, n, "sequential", "none", 1, 0, samples, memory, status)

        for threads in thread_counts:
            samples, memory, status = measure(
                multiply_parallel, (a, b, threads), expected
            )
            add_pending(pending, n, "parallel", "none", threads, 0, samples, memory, status)

        samples, memory, status = measure(
            multiply_vectorized, (a, b), expected
        )
        add_pending(
            pending, n, "vectorized", "numpy-matmul", 1, 1,
            samples, memory, status,
        )

    medians: dict[tuple[int, str, int], float] = {}
    for item in pending:
        n, method, _, threads, _, samples, _, status = item
        if status == "ok" and samples:
            medians[(n, method, threads)] = statistics.median(samples)

    raw: list[dict[str, object]] = []
    for item in pending:
        n, method, variant, threads, internal_threads, samples, memory, status = item
        baseline = medians.get((n, "sequential", 1))
        current = medians.get((n, method, threads))
        speedup = ""
        efficiency = ""
        if baseline is not None and current is not None:
            speedup = f"{baseline / current:.6f}"
            if method == "sequential":
                efficiency = "1.000000"
            elif method == "parallel":
                efficiency = f"{baseline / current / threads:.6f}"

        for repetition, time_ms in enumerate(samples, 1):
            raw.append(
                {
                    "size": n,
                    "method": method,
                    "variant": variant,
                    "threads": threads,
                    "internal_threads": internal_threads,
                    "repetition": repetition,
                    "time_ms": f"{time_ms:.6f}",
                    "peak_memory_mib": f"{memory:.6f}",
                    "status": status,
                    "speedup": speedup,
                    "efficiency": efficiency,
                }
            )

    write_raw(ROOT / "results.csv", raw)
    write_summary(ROOT / "summary.csv", raw)
    environment = {
        "assignment": 3,
        "run_timestamp": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "python_version": sys.version,
        "operating_system": platform.platform(),
        "seed": SEED,
        "sizes": sizes,
        "thread_counts": thread_counts,
        "repetitions": REPETITIONS,
        "warmups": WARMUPS,
        "time_limit_seconds": TIME_LIMIT_SECONDS,
        "memory_limit_mib": MEMORY_LIMIT_MIB,
        "memory_metric": "Python traced allocation peak via tracemalloc",
        "timing_boundary": "multiplication call only; generation and validation excluded",
        "parallel_framework": "concurrent.futures.ThreadPoolExecutor",
        "thread_safety": "each worker writes a distinct output row",
        "logical_processors": os.cpu_count(),
        "physical_cores": physical_core_count(),
        "affinity": "OS scheduler default; no affinity pinning",
        "internal_library_threads": 0,
        "numeric_type": "Python float / NumPy float64",
        "vectorisation": "NumPy matmul",
        "vectorisation_library": "numpy==2.3.4",
        "vectorisation_internal_threads": 1,
        "vectorisation_thread_controls": {
            "OMP_NUM_THREADS": os.environ["OMP_NUM_THREADS"],
            "MKL_NUM_THREADS": os.environ["MKL_NUM_THREADS"],
            "OPENBLAS_NUM_THREADS": os.environ["OPENBLAS_NUM_THREADS"],
        },
        "vectorisation_evidence": (
            "NumPy matmul backend recorded; no disassembly was performed."
        ),
    }
    (ROOT / "environment.json").write_text(
        json.dumps(environment, indent=2),
        encoding="utf-8",
    )
    configurations = {
        (row["size"], row["method"], row["variant"], row["threads"])
        for row in raw
    }
    return {"raw_measurements": len(raw), "configurations": len(configurations)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=DEFAULT_SIZES)
    parser.add_argument("--threads", nargs="+", type=int, default=DEFAULT_THREADS)
    args = parser.parse_args()
    if any(n <= 0 for n in args.sizes) or any(t <= 0 for t in args.threads):
        parser.error("sizes and thread counts must be positive")
    tracemalloc.start()
    print(json.dumps(run(args.sizes, args.threads)))


if __name__ == "__main__":
    main()

"""Reproducible benchmark for Assignment 3."""

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

from methods import (
    Matrix,
    assert_close,
    multiply_parallel,
    multiply_sequential,
)


ROOT = Path(__file__).resolve().parent

DEFAULT_SIZES = [32, 64, 96, 128]
DEFAULT_THREADS = [1, 2, 4, 8]

SEED = 20261112
REPETITIONS = 5
WARMUPS = 1

TIME_LIMIT_SECONDS = 60.0
MEMORY_LIMIT_MIB = 2048.0


def make_matrix(
    rng: random.Random,
    size: int,
) -> Matrix:
    """Generate a deterministic square matrix."""
    return [
        [
            float(rng.randint(-8, 8))
            for _ in range(size)
        ]
        for _ in range(size)
    ]


def calculate_iqr(values: list[float]) -> float:
    """Calculate the inclusive interquartile range."""
    if len(values) < 2:
        return 0.0

    quartiles = statistics.quantiles(
        values,
        n=4,
        method="inclusive",
    )

    return quartiles[2] - quartiles[0]


def get_physical_core_count() -> int | None:
    """Read the physical-core count on Windows."""
    if os.name != "nt":
        return None

    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        (
            "(Get-CimInstance Win32_Processor | "
            "Measure-Object -Property NumberOfCores -Sum).Sum"
        ),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    value = result.stdout.strip()

    if value.isdigit():
        return int(value)

    return None


def measure_configuration(
    method,
    arguments: tuple,
    expected: Matrix,
) -> tuple[list[float], float, str]:
    """Run warm-ups and timed repetitions for one configuration."""
    for _ in range(WARMUPS):
        warmup_result = method(*arguments)
        assert_close(warmup_result, expected)

    tracemalloc.reset_peak()

    samples: list[float] = []
    configuration_started = time.perf_counter()
    status = "ok"

    for _ in range(REPETITIONS):
        sample_started = time.perf_counter()

        result = method(*arguments)

        elapsed_ms = (
            time.perf_counter() - sample_started
        ) * 1000.0

        assert_close(result, expected)
        samples.append(elapsed_ms)

        total_seconds = (
            time.perf_counter() - configuration_started
        )

        if total_seconds > TIME_LIMIT_SECONDS:
            status = "timeout"
            break

    peak_bytes = tracemalloc.get_traced_memory()[1]
    peak_memory_mib = peak_bytes / (1024 * 1024)

    if peak_memory_mib > MEMORY_LIMIT_MIB:
        status = "memory_limit"

    return samples, peak_memory_mib, status


def append_raw_rows(
    rows: list[dict[str, object]],
    *,
    size: int,
    method: str,
    threads: int,
    samples: list[float],
    peak_memory_mib: float,
    status: str,
) -> None:
    """Append one raw CSV row per measured repetition."""
    for repetition, time_ms in enumerate(samples, start=1):
        rows.append(
            {
                "size": size,
                "method": method,
                "threads": threads,
                "repetition": repetition,
                "time_ms": f"{time_ms:.6f}",
                "peak_memory_mib": f"{peak_memory_mib:.6f}",
                "status": status,
            }
        )


def write_raw_results(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    """Write all raw measurements."""
    fields = [
        "size",
        "method",
        "threads",
        "repetition",
        "time_ms",
        "peak_memory_mib",
        "status",
    ]

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as output:
        writer = csv.DictWriter(
            output,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def write_summary(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    """Write medians, IQR, speedup and efficiency."""
    grouped: dict[
        tuple[str, str, str],
        list[dict[str, object]],
    ] = {}

    for row in rows:
        key = (
            str(row["size"]),
            str(row["method"]),
            str(row["threads"]),
        )

        grouped.setdefault(key, []).append(row)

    sequential_medians: dict[str, float] = {}

    for key, group in grouped.items():
        size, method, _ = key

        if method != "sequential":
            continue

        values = [
            float(row["time_ms"])
            for row in group
            if row["status"] == "ok"
        ]

        if values:
            sequential_medians[size] = statistics.median(values)

    fields = [
        "size",
        "method",
        "threads",
        "median_ms",
        "iqr_ms",
        "peak_memory_mib",
        "samples",
        "status",
        "speedup",
        "efficiency",
    ]

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as output:
        writer = csv.DictWriter(
            output,
            fieldnames=fields,
        )
        writer.writeheader()

        for key, group in grouped.items():
            size, method, thread_text = key

            values = [
                float(row["time_ms"])
                for row in group
                if row["status"] == "ok"
            ]

            if values:
                median_ms = statistics.median(values)
                iqr_ms = calculate_iqr(values)
            else:
                median_ms = None
                iqr_ms = None

            baseline = sequential_medians.get(size)

            if method == "sequential":
                speedup = 1.0
                efficiency = 1.0
            elif baseline is not None and median_ms is not None:
                speedup = baseline / median_ms
                efficiency = speedup / int(thread_text)
            else:
                speedup = None
                efficiency = None

            writer.writerow(
                {
                    "size": size,
                    "method": method,
                    "threads": thread_text,
                    "median_ms": (
                        f"{median_ms:.6f}"
                        if median_ms is not None
                        else ""
                    ),
                    "iqr_ms": (
                        f"{iqr_ms:.6f}"
                        if iqr_ms is not None
                        else ""
                    ),
                    "peak_memory_mib": group[-1][
                        "peak_memory_mib"
                    ],
                    "samples": f"{len(values)}/{len(group)}",
                    "status": group[-1]["status"],
                    "speedup": (
                        f"{speedup:.6f}"
                        if speedup is not None
                        else ""
                    ),
                    "efficiency": (
                        f"{efficiency:.6f}"
                        if efficiency is not None
                        else ""
                    ),
                }
            )


def run_benchmark(
    sizes: list[int],
    thread_counts: list[int],
) -> dict[str, object]:
    """Run the sequential and parallel comparison."""
    rng = random.Random(SEED)
    rows: list[dict[str, object]] = []

    for size in sizes:
        matrix_a = make_matrix(rng, size)
        matrix_b = make_matrix(rng, size)

        expected = multiply_sequential(
            matrix_a,
            matrix_b,
        )

        sequential_samples, sequential_memory, sequential_status = (
            measure_configuration(
                multiply_sequential,
                (matrix_a, matrix_b),
                expected,
            )
        )

        append_raw_rows(
            rows,
            size=size,
            method="sequential",
            threads=1,
            samples=sequential_samples,
            peak_memory_mib=sequential_memory,
            status=sequential_status,
        )

        for thread_count in thread_counts:
            parallel_samples, parallel_memory, parallel_status = (
                measure_configuration(
                    multiply_parallel,
                    (
                        matrix_a,
                        matrix_b,
                        thread_count,
                    ),
                    expected,
                )
            )

            append_raw_rows(
                rows,
                size=size,
                method="parallel",
                threads=thread_count,
                samples=parallel_samples,
                peak_memory_mib=parallel_memory,
                status=parallel_status,
            )

    write_raw_results(
        ROOT / "results.csv",
        rows,
    )

    write_summary(
        ROOT / "summary.csv",
        rows,
    )

    environment = {
        "assignment": 3,
        "run_timestamp": (
            dt.datetime.now()
            .astimezone()
            .isoformat(timespec="seconds")
        ),
        "python_version": sys.version,
        "operating_system": platform.platform(),
        "seed": SEED,
        "sizes": sizes,
        "thread_counts": thread_counts,
        "repetitions": REPETITIONS,
        "warmups": WARMUPS,
        "time_limit_seconds": TIME_LIMIT_SECONDS,
        "memory_limit_mib": MEMORY_LIMIT_MIB,
        "memory_metric": (
            "Python traced allocation peak via tracemalloc"
        ),
        "timing_boundary": (
            "multiplication call only; input generation, "
            "allocation and validation excluded"
        ),
        "parallel_framework": (
            "concurrent.futures.ThreadPoolExecutor"
        ),
        "thread_safety": (
            "each worker calculates a different complete output row"
        ),
        "logical_processors": os.cpu_count(),
        "physical_cores": get_physical_core_count(),
        "affinity": "OS scheduler default; no affinity pinning",
        "internal_library_threads": 0,
        "numeric_type": "Python float",
        "vectorisation": "not undertaken",
    }

    (ROOT / "environment.json").write_text(
        json.dumps(
            environment,
            indent=2,
        ),
        encoding="utf-8",
    )

    configurations = {
        (
            row["size"],
            row["method"],
            row["threads"],
        )
        for row in rows
    }

    return {
        "raw_measurements": len(rows),
        "configurations": len(configurations),
    }


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=DEFAULT_SIZES,
    )

    parser.add_argument(
        "--threads",
        nargs="+",
        type=int,
        default=DEFAULT_THREADS,
    )

    args = parser.parse_args()

    if any(size <= 0 for size in args.sizes):
        parser.error("all sizes must be positive")

    if any(thread_count <= 0 for thread_count in args.threads):
        parser.error("all thread counts must be positive")

    tracemalloc.start()

    result = run_benchmark(
        args.sizes,
        args.threads,
    )

    print(json.dumps(result))


if __name__ == "__main__":
    main()
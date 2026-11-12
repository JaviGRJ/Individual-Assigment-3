"""Sequential and threaded matrix multiplication for Assignment 3."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TypeAlias

Matrix: TypeAlias = list[list[float]]


def zeros(n: int) -> Matrix:
    return [[0.0] * n for _ in range(n)]


def multiply_sequential(a: Matrix, b: Matrix) -> Matrix:
    """Sequential i-j-k baseline."""
    n = len(a)
    c = zeros(n)
    for i in range(n):
        for j in range(n):
            total = 0.0
            for k in range(n):
                total += a[i][k] * b[k][j]
            c[i][j] = total
    return c


def _multiply_row(args: tuple[Matrix, Matrix, int]) -> list[float]:
    a, b, i = args
    n = len(a)
    row: list[float] = []
    for j in range(n):
        total = 0.0
        for k in range(n):
            total += a[i][k] * b[k][j]
        row.append(total)
    return row


def multiply_parallel(a: Matrix, b: Matrix, threads: int) -> Matrix:
    """Threaded multiplication where each worker owns complete output rows."""
    if threads < 1:
        raise ValueError("threads must be at least one")
    n = len(a)
    arguments = ((a, b, i) for i in range(n))
    with ThreadPoolExecutor(max_workers=threads) as executor:
        return list(executor.map(_multiply_row, arguments))


def assert_close(actual: Matrix, expected: Matrix, tolerance: float = 1e-12) -> None:
    if len(actual) != len(expected):
        raise AssertionError("matrix dimensions differ")
    for i, (actual_row, expected_row) in enumerate(zip(actual, expected)):
        for j, (actual_value, expected_value) in enumerate(zip(actual_row, expected_row)):
            allowed = tolerance + tolerance * abs(expected_value)
            if abs(actual_value - expected_value) > allowed:
                raise AssertionError(
                    f"mismatch at ({i}, {j}): {actual_value} != {expected_value}"
                )


def self_test() -> None:
    a = [[1.0, 2.0], [3.0, 4.0]]
    b = [[5.0, 6.0], [7.0, 8.0]]
    expected = [[19.0, 22.0], [43.0, 50.0]]
    assert_close(multiply_sequential(a, b), expected)
    for threads in (1, 2):
        assert_close(multiply_parallel(a, b, threads), expected)


if __name__ == "__main__":
    self_test()
    print("Assignment 3 method self-tests passed.")

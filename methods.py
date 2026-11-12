"""Sequential and threaded matrix multiplication for Assignment 3."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TypeAlias


Matrix: TypeAlias = list[list[float]]


def zeros(n: int) -> Matrix:
    """Create an n by n matrix filled with zeros."""
    return [[0.0] * n for _ in range(n)]


def multiply_sequential(a: Matrix, b: Matrix) -> Matrix:
    """Sequential i-j-k matrix multiplication."""
    n = len(a)
    c = zeros(n)

    for i in range(n):
        for j in range(n):
            total = 0.0

            for k in range(n):
                total += a[i][k] * b[k][j]

            c[i][j] = total

    return c


def multiply_row(
    arguments: tuple[Matrix, Matrix, int],
) -> list[float]:
    """Calculate one complete output row."""
    a, b, row_index = arguments
    n = len(a)
    result_row: list[float] = []

    for j in range(n):
        total = 0.0

        for k in range(n):
            total += a[row_index][k] * b[k][j]

        result_row.append(total)

    return result_row


def multiply_parallel(
    a: Matrix,
    b: Matrix,
    threads: int,
) -> Matrix:
    """Threaded multiplication assigning complete rows to workers."""
    if threads < 1:
        raise ValueError("threads must be at least 1")

    arguments = (
        (a, b, row_index)
        for row_index in range(len(a))
    )

    with ThreadPoolExecutor(max_workers=threads) as executor:
        return list(executor.map(multiply_row, arguments))


def assert_close(
    actual: Matrix,
    expected: Matrix,
    tolerance: float = 1e-12,
) -> None:
    """Compare two matrices using absolute and relative tolerance."""
    if len(actual) != len(expected):
        raise AssertionError("matrix dimensions differ")

    for row_index, (actual_row, expected_row) in enumerate(
        zip(actual, expected)
    ):
        if len(actual_row) != len(expected_row):
            raise AssertionError(
                f"row {row_index} dimensions differ"
            )

        for column_index, (actual_value, expected_value) in enumerate(
            zip(actual_row, expected_row)
        ):
            allowed_error = (
                tolerance
                + tolerance * abs(expected_value)
            )

            if abs(actual_value - expected_value) > allowed_error:
                raise AssertionError(
                    f"mismatch at ({row_index}, {column_index}): "
                    f"{actual_value} != {expected_value}"
                )


def self_test() -> None:
    """Run correctness tests for both implementations."""
    matrix_a = [
        [1.0, 2.0],
        [3.0, 4.0],
    ]

    matrix_b = [
        [5.0, 6.0],
        [7.0, 8.0],
    ]

    expected = [
        [19.0, 22.0],
        [43.0, 50.0],
    ]

    sequential_result = multiply_sequential(
        matrix_a,
        matrix_b,
    )

    assert_close(
        sequential_result,
        expected,
    )

    for thread_count in (1, 2):
        parallel_result = multiply_parallel(
            matrix_a,
            matrix_b,
            thread_count,
        )

        assert_close(
            parallel_result,
            expected,
        )


if __name__ == "__main__":
    self_test()
    print("Assignment 3 method self-tests passed.")
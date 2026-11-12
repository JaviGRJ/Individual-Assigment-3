"""Optional NumPy vectorized multiplication for Assignment 3."""

from __future__ import annotations

from typing import TypeAlias

import numpy as np

Matrix: TypeAlias = list[list[float]]


def multiply_vectorized(a: Matrix, b: Matrix) -> Matrix:
    """Multiply matrices through NumPy's vectorized matmul operation."""
    result = np.matmul(np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64))
    return result.tolist()


def self_test() -> None:
    a = [[1.0, 2.0], [3.0, 4.0]]
    b = [[5.0, 6.0], [7.0, 8.0]]
    expected = [[19.0, 22.0], [43.0, 50.0]]
    actual = multiply_vectorized(a, b)
    for actual_row, expected_row in zip(actual, expected):
        for actual_value, expected_value in zip(actual_row, expected_row):
            if abs(actual_value - expected_value) > 1e-12:
                raise AssertionError("vectorized self-test failed")


if __name__ == "__main__":
    self_test()
    print("Assignment 3 vectorized self-test passed.")

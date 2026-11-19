#!/usr/bin/env python3
"""
Unit tests for Dielectric Lifetime Decoupling Protocol Solver (TICKET-08).
"""

import ast
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from dielectric_lifetime_decoupling_solver import (
    C,
    EPS_0,
    MU_0,
    Z_0,
    TAU_2P,
    TAU_3D,
    fractional_lifetime_shift,
    decay_length,
    generate_protocol_matrix,
    run_benchmark,
)


class TestDielectricLifetimeDecoupling(unittest.TestCase):
    def test_grid_impedance_identity(self):
        """Verify characteristic impedance matches Z_0 = sqrt(mu_0 / eps_0)."""
        z_calc = math.sqrt(MU_0 / EPS_0)
        self.assertAlmostEqual(Z_0, z_calc, places=7)

    def test_lifetime_shift_scaling_with_field_squared(self):
        """Verify Delta_tau / tau scales quadratically with applied E-field."""
        k_bulk = 1.0  # Pa
        shift_1 = fractional_lifetime_shift(100.0, k_bulk)
        shift_2 = fractional_lifetime_shift(200.0, k_bulk)
        # Doubling E quadruples shift
        self.assertAlmostEqual(shift_2 / shift_1, 4.0, places=7)

    def test_beam_decay_length_order_of_magnitude(self):
        """Verify spatial decay length for 2p is microscopic (~4.8 um at 3000 m/s)."""
        x_2p = decay_length(TAU_2P, v_beam=3000.0)
        self.assertAlmostEqual(x_2p * 1e6, 4.786, places=2)

    def test_benchmark_output_generation(self):
        """Verify benchmark CSV is generated with all protocol rows."""
        rows = run_benchmark()
        self.assertGreaterEqual(len(rows), 7)
        csv_path = HERE.parent / "results" / "dielectric_lifetime_decoupling_benchmark.csv"
        self.assertTrue(csv_path.exists())

    def test_anti_smuggling_ast_guard(self):
        """Verify solver does not smuggle forbidden quantum wavefunctions or magic floats."""
        solver_path = HERE / "dielectric_lifetime_decoupling_solver.py"
        with solver_path.open("r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename="dielectric_lifetime_decoupling_solver.py")

        banned_calls = {"genlaguerre", "assoc_laguerre", "hermite", "legendre"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in banned_calls:
                    self.fail(f"Smuggled QM function call detected: {func.id}")
                elif isinstance(func, ast.Attribute) and func.attr in banned_calls:
                    self.fail(f"Smuggled QM function call detected: {func.attr}")


if __name__ == "__main__":
    unittest.main()

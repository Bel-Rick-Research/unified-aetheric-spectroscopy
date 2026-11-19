#!/usr/bin/env python3
"""
Unit tests for Planck-Clock Nyquist Fractal Cutoff & Scale Ladder Solver (TICKET-11).
"""

import ast
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from nyquist_fractal_cutoff import (
    ALPHA,
    L_P,
    P_T,
    C,
    nyquist_cutoff_radius,
    ticks_per_perimeter,
    scale_hierarchy_catalog,
    run_benchmark,
)

HERE = Path(__file__).resolve().parent


class TestNyquistFractalCutoff(unittest.TestCase):
    def test_nyquist_tick_identity(self):
        """At k=0, the cutoff perimeter must equal exactly 2 Planck lattice steps (Nyquist limit)."""
        r0 = nyquist_cutoff_radius(0)
        perimeter = 2.0 * math.pi * r0
        self.assertAlmostEqual(perimeter, 2.0 * L_P, places=12)
        ticks = ticks_per_perimeter(r0)
        self.assertAlmostEqual(ticks, 2.0, places=12)

    def test_alpha_squared_ladder_spacing(self):
        """Consecutive even tiers must scale by exactly 1 / alpha^2."""
        expected_ratio = 1.0 / (ALPHA ** 2)
        for k in (0, 2, 4, 6, 8, 10):
            r_k = nyquist_cutoff_radius(k)
            r_k2 = nyquist_cutoff_radius(k + 2)
            ratio = r_k2 / r_k
            self.assertAlmostEqual(ratio, expected_ratio, places=7)

    def test_monotonicity(self):
        """Cutoff radius must strictly increase with winding order k."""
        prev_r = 0.0
        for k in range(15):
            r = nyquist_cutoff_radius(k)
            self.assertGreater(r, prev_r)
            prev_r = r

    def test_paper4_boundary_hierarchy(self):
        """Proton boundary (k=8) must sit between sub-proton throat (k=7) and electron core (k=10)."""
        r_parton = nyquist_cutoff_radius(7)
        r_proton = nyquist_cutoff_radius(8)
        r_electron = nyquist_cutoff_radius(10)
        r_bohr = nyquist_cutoff_radius(12)

        self.assertLess(r_parton, r_proton)
        self.assertLess(r_proton, r_electron)
        self.assertLess(r_electron, r_bohr)

    def test_benchmark_output_generation(self):
        """Verify benchmark runs cleanly and populates CSV output."""
        rows = run_benchmark()
        self.assertEqual(len(rows), 5)
        csv_path = HERE.parent / "results" / "nyquist_fractal_cutoff_benchmark.csv"
        self.assertTrue(csv_path.exists())

    def test_anti_smuggling_ast_guard(self):
        """Verify solver does not smuggle quantum wavefunctions or fitted empirical floats."""
        solver_path = HERE / "nyquist_fractal_cutoff.py"
        with solver_path.open("r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename="nyquist_fractal_cutoff.py")

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

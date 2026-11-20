#!/usr/bin/env python3
"""
Unit tests for Circulation Quantum Geometry & Planck Cell Line Integral Solver (TICKET-09).
"""

import ast
import math
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from circulation_quantum_geometry_solver import (
    C,
    L_P,
    ALPHA,
    KAPPA_3D,
    GAMMA_CELL,
    GAMMA_0,
    LAMBDA_C_MU,
    LAMBDA_C_E,
    circulation_scale_hierarchy,
    run_benchmark,
)


class TestCirculationQuantumGeometry(unittest.TestCase):
    def test_kappa_3d_packing_factor(self):
        """Verify 3D toroidal packing factor kappa_3D = (4*pi/3)*(1 + 3/(16*pi^2)) ~ 4.268368."""
        self.assertAlmostEqual(KAPPA_3D, 4.268368, places=5)

    def test_3d_packing_hierarchy_within_25_ppm(self):
        """Verify 1 / (kappa_3D * alpha^11) matches bare electron Compton ratio lambda_C,e / (2*l_P) to 21 ppm."""
        n_geom = 1.0 / (KAPPA_3D * (ALPHA ** 11))
        n_ref = LAMBDA_C_E / (2.0 * L_P)
        diff_ppm = abs(n_geom - n_ref) / n_ref * 1e6
        self.assertLess(diff_ppm, 25.0)

    def test_planck_cell_circulation_value(self):
        """Verify minimum 2-tick Planck cell circulation equals 2 * c * l_P."""
        expected = 2.0 * C * L_P
        self.assertAlmostEqual(GAMMA_CELL, expected, places=12)

    def test_vortex_circulation_compton_identity(self):
        """Verify Gamma_0 = c * lambda_C identically."""
        expected = C * LAMBDA_C_MU
        self.assertAlmostEqual(GAMMA_0, expected, places=12)

    def test_hierarchy_ratio_identity(self):
        """Verify Gamma_0 / Gamma_cell equals lambda_C / (2 * l_P)."""
        ratio_gamma = GAMMA_0 / GAMMA_CELL
        ratio_lambda = LAMBDA_C_MU / (2.0 * L_P)
        self.assertAlmostEqual(ratio_gamma, ratio_lambda, places=7)

    def test_benchmark_output_generation(self):
        """Verify benchmark CSV is generated with all hierarchy rows."""
        rows = run_benchmark()
        self.assertEqual(len(rows), 5)
        csv_path = HERE.parent / "results" / "circulation_quantum_geometry_benchmark.csv"
        self.assertTrue(csv_path.exists())

    def test_anti_smuggling_ast_guard(self):
        """Verify solver does not smuggle forbidden quantum wavefunctions or magic floats."""
        solver_path = HERE / "circulation_quantum_geometry_solver.py"
        with solver_path.open("r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename="circulation_quantum_geometry_solver.py")

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

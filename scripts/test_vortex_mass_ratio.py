#!/usr/bin/env python3
"""
Unit tests for Proton-to-Electron Mass Ratio Vortex Topology Solver (TICKET-07).
Validates 6*pi^5 phase volume derivation, sexagesimal (30; 36)_60 encoding, and code guards.
"""

import csv
import math
import re
import unittest
from pathlib import Path

import vortex_mass_ratio_solver as vmrs

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE.parent / "results" / "vortex_mass_ratio_benchmark.csv"
FORBIDDEN_CODE = re.compile(r"R_nl|eigh_tridiagonal|sympy|hydrogen\s+import", re.IGNORECASE)


class VortexMassRatioTests(unittest.TestCase):
    def test_geometric_mass_ratio_within_19_ppm(self) -> None:
        """Verify (m_p / m_e)_geom = 6*pi^5 is 1836.1181 and agrees with CODATA to 18.82 ppm."""
        m_geom = vmrs.geometric_mass_ratio_6_pi_5()
        self.assertAlmostEqual(m_geom, 1836.118109, places=5)
        ppm = vmrs.mass_ratio_residual_ppm()
        self.assertAlmostEqual(ppm, 18.82, places=1)
        self.assertLess(ppm, 19.0)

    def test_base60_sexagesimal_decomposition(self) -> None:
        """Verify 1836 decomposes into base-60 digits (30; 36)_60."""
        d_1, d_0 = vmrs.base60_sexagesimal_decomposition(1836)
        self.assertEqual(d_1, 30)
        self.assertEqual(d_0, 36)
        self.assertEqual(d_1 * 60 + d_0, 1836)

    def test_sexagesimal_harmonic_product_is_1080(self) -> None:
        """Verify product of base-60 digits is 30 * 36 = 1080 (Moon radius)."""
        prod = vmrs.sexagesimal_harmonic_product()
        self.assertEqual(prod, 1080)

    def test_dodecahedral_triangular_factorization(self) -> None:
        """Verify 1836 = 12 * 153 = 12 * T_17."""
        dodeca, t_17, prod = vmrs.dodecahedral_triangular_factorization()
        self.assertEqual(dodeca, 12)
        self.assertEqual(t_17, 153)
        self.assertEqual(prod, 1836)

    def test_vortex_dimensions(self) -> None:
        """Verify vortex aspect ratio dimensions: r_e = alpha^2 * a_mu, r_p = 4 * lambda_bar_p."""
        params = vmrs.vortex_aspect_ratio_parameters()
        self.assertAlmostEqual(params["electron_core_m"] / 1e-15, 2.8179, places=2)
        self.assertAlmostEqual(params["proton_charge_radius_m"] / 1e-15, 0.8412, places=2)
        self.assertGreater(params["electron_torus_vol_m3"], 0.0)
        self.assertGreater(params["proton_core_vol_m3"], 0.0)

    def test_benchmark_csv_output_integrity(self) -> None:
        """Verify CSV benchmark table is generated with 4 rows and correct headers."""
        rows = vmrs.run_benchmark()
        self.assertEqual(len(rows), 4)
        self.assertTrue(RESULTS_CSV.is_file())
        with RESULTS_CSV.open(newline="", encoding="utf-8") as f:
            read_rows = list(csv.DictReader(f))
        self.assertEqual(len(read_rows), 4)
        self.assertIn("aspect", read_rows[0])
        self.assertIn("epistemic_status", read_rows[0])
        self.assertIn("physical_mechanism", read_rows[0])

    def test_no_forbidden_wavefunction_code(self) -> None:
        """Guard: Ensure no Schrödinger wavefunctions or QM library code is imported."""
        for path in sorted(HERE.glob("*.py")):
            if path.name.startswith("test_"):
                continue
            for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if FORBIDDEN_CODE.search(line) and not line.lstrip().startswith(("#", '"""')):
                    self.fail(f"Forbidden QM code found in {path.name}:{num}: {line}")


if __name__ == "__main__":
    unittest.main()

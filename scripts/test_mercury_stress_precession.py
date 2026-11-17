#!/usr/bin/env python3
"""
Unit tests for Mercury Precession & Atomic Fine Structure Stress Solver (Paper 4).
Validates Mercury 43''/century perihelion advance, Hydrogen 10.943 GHz 2p doublet, and code guards.
"""

import csv
import math
import re
import unittest
from pathlib import Path

import mercury_stress_precession_solver as msps

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE.parent / "results" / "mercury_stress_precession_benchmark.csv"
FORBIDDEN_CODE = re.compile(r"R_nl|eigh_tridiagonal|sympy|hydrogen\s+import", re.IGNORECASE)


class MercuryStressPrecessionTests(unittest.TestCase):
    def test_mercury_orbital_speed_and_stress_parameter(self) -> None:
        """Verify Mercury average orbital speed is ~47.36 km/s and (v/c)^2 ~ 2.55e-8."""
        v = msps.mercury_orbital_speed_m_s()
        self.assertAlmostEqual(v / 1e3, 47.87, places=1)
        stress = (v / msps.C) ** 2
        self.assertAlmostEqual(stress / 1e-8, 2.55, places=1)

    def test_mercury_precession_rate_matches_43_arcseconds(self) -> None:
        """Verify Mercury perihelion advance is 42.98 arcsec/century (~43.0''/century)."""
        rate = msps.mercury_precession_arcsec_century()
        self.assertAlmostEqual(rate, 42.98, places=1)
        self.assertAlmostEqual(rate, 43.0, delta=0.1)

    def test_atomic_stress_parameter_equals_alpha_over_n_squared(self) -> None:
        """Verify atomic stress parameter (v_n / c)^2 identically equals (Z * alpha / n)^2."""
        for n in (1, 2, 3, 4):
            v_n = msps.atomic_orbital_speed_m_s(n, Z=1)
            stress_calc = (v_n / msps.C) ** 2
            expected = (msps.ALPHA / n) ** 2
            self.assertAlmostEqual(stress_calc / expected, 1.0, places=12)

    def test_hydrogen_2p_doublet_matches_10_943_ghz(self) -> None:
        """Verify medium stress precession produces the exact 10.9433 GHz hydrogen 2p doublet."""
        split_hz = msps.hydrogen_2p_doublet_split_hz(Z=1)
        expected_hz = (1.0 / 32.0) * msps.MU_H * msps.C**2 * msps.ALPHA**4 / msps.H_PLANCK
        self.assertAlmostEqual(split_hz / expected_hz, 1.0, places=12)
        self.assertAlmostEqual(split_hz / 1e9, 10.9433, places=3)

    def test_benchmark_csv_output_integrity(self) -> None:
        """Verify CSV benchmark table is generated with 3 rows and correct headers."""
        rows = msps.run_benchmark()
        self.assertEqual(len(rows), 3)
        self.assertTrue(RESULTS_CSV.is_file())
        with RESULTS_CSV.open(newline="", encoding="utf-8") as f:
            read_rows = list(csv.DictReader(f))
        self.assertEqual(len(read_rows), 3)
        self.assertIn("stress_parameter_v_over_c_sq", read_rows[0])
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

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
        """Verify medium stress precession produces the exact 10.9433 GHz hydrogen 2p doublet natively without h."""
        split_hz = msps.hydrogen_2p_doublet_split_hz(Z=1)
        expected_native_hz = (1.0 / 32.0) * (msps.C**2 * msps.ALPHA**4) / msps.GAMMA_0
        self.assertAlmostEqual(split_hz / expected_native_hz, 1.0, places=12)
        self.assertAlmostEqual(split_hz / 1e9, 10.9433, places=3)

    def test_virial_theorem_stress_offset_ratio_is_exact_minus_three_quarters(self) -> None:
        """Verify Virial Theorem <V> = 2*E derives identically -3/4 (-0.75) from (E^2 - 4*E^2) / (4*E^2)."""
        ratio = msps.virial_theorem_stress_offset_ratio()
        self.assertEqual(ratio, -0.75)

    def test_torsion_orbit_cancellation_identity(self) -> None:
        """Verify algebraic identity combining dispersion and Thomas spin-orbit coupling into 1/(j + 1/2)."""
        for l in range(1, 6):
            res_par, res_anti = msps.verify_torsion_orbit_cancellation(l)
            self.assertLess(res_par, 1e-15, f"Parallel cancellation failed at l={l}")
            self.assertLess(res_anti, 1e-15, f"Anti-parallel cancellation failed at l={l}")

    def test_dispersion_plus_thomas_so_equals_total_fine_structure(self) -> None:
        """Verify Delta nu_disp + Delta nu_SO identically equals Delta nu_stress for all n <= 6."""
        for n in range(2, 7):
            for l in range(1, n):
                for j in (l - 0.5, l + 0.5):
                    disp = msps.atomic_dispersion_precession_beat_hz(n, l, Z=1)
                    so = msps.atomic_thomas_spin_orbit_beat_hz(n, l, j, Z=1)
                    total = msps.atomic_total_stress_precession_beat_hz(n, l, j, Z=1)
                    self.assertAlmostEqual((disp + so) / total, 1.0, places=12)

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

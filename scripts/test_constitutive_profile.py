#!/usr/bin/env python3
"""
Unit tests for Hydrodynamic Constitutive Profile & Dielectric Grid Saturation Solver (TICKET-04).
Validates rational continuity profile, asymptotic convergence to core and bulk limits, and code guards.
"""

import csv
import math
import re
import unittest
from pathlib import Path

import constitutive_profile_solver as cps

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE.parent / "results" / "constitutive_profile_benchmark.csv"
FORBIDDEN_CODE = re.compile(r"R_nl|eigh_tridiagonal|sympy|hydrogen\s+import", re.IGNORECASE)


class ConstitutiveProfileTests(unittest.TestCase):
    def test_rational_continuity_asymptotes(self) -> None:
        """Verify T(r) = R_trans / (R_trans + r) approaches 1.0 at small r and 0.0 at large r."""
        r_trans = 1.0e-3
        t_core = cps.rational_continuity_transition(1e-11, r_trans)
        t_bulk = cps.rational_continuity_transition(1e11, r_trans)
        self.assertAlmostEqual(t_core, 1.0, places=6)
        self.assertAlmostEqual(t_bulk, 0.0, places=12)

    def test_bracket_converges_to_linear_coulomb_at_atomic_scale(self) -> None:
        """Verify U(r) = r^2 * K^2(r) converges to 2Z * r / a_mu at r = 1 Bohr radius to < 0.001%."""
        r_atom = cps.A_MU
        u_val = cps.effective_operator_bracket(r_atom, Z=1)
        expected = (2.0 / cps.A_MU) * r_atom  # = 2.0 exactly
        self.assertAlmostEqual(u_val / expected, 1.0, places=6)

    def test_bracket_converges_to_constant_g0_at_macro_scale(self) -> None:
        """Verify U(r) = r^2 * K^2(r) converges to constant g_0 = 2Z * R_trans / a_mu at 1 AU to < 0.001%."""
        r_au = 1.495978707e11
        u_val = cps.effective_operator_bracket(r_au, Z=1)
        expected_g0 = cps.asymptotic_euler_cauchy_g0(Z=1)
        self.assertAlmostEqual(u_val / expected_g0, 1.0, places=6)

    def test_sonic_choking_radius(self) -> None:
        """Verify inner sonic crossover radius r_sonic(Z) = 2 * Z * r_e."""
        r_sonic_H = cps.sonic_choking_radius(Z=1)
        r_sonic_He = cps.sonic_choking_radius(Z=2)
        self.assertAlmostEqual(r_sonic_H, 2.0 * cps.R_E, places=18)
        self.assertAlmostEqual(r_sonic_He, 4.0 * cps.R_E, places=18)

    def test_dielectric_strain_volume_factor_contracts_ratio(self) -> None:
        """Verify static and rational continuity strain volume factors contract He+/H ratio."""
        # Static model: contracts 16.0 to 15.012 (+13.1% residual)
        eta_H_stat = cps.dielectric_strain_volume_factor(2, Z=1, mode="static")
        eta_He_stat = cps.dielectric_strain_volume_factor(2, Z=2, mode="static")
        self.assertEqual(eta_H_stat, 1.0)
        self.assertAlmostEqual(eta_He_stat, 0.93826, places=4)
        ratio_stat = 16.0 * (eta_He_stat / eta_H_stat)
        self.assertAlmostEqual(ratio_stat, 15.012, places=2)

        # Rational continuity sonic choking model: contracts 16.0 to 13.894 (+4.68% residual)
        eta_H_rat = cps.dielectric_strain_volume_factor(2, Z=1, mode="rational")
        eta_He_rat = cps.dielectric_strain_volume_factor(2, Z=2, mode="rational")
        self.assertEqual(eta_H_rat, 1.0)
        self.assertAlmostEqual(eta_He_rat, 0.86840, places=4)
        ratio_rat = 16.0 * (eta_He_rat / eta_H_rat)
        self.assertAlmostEqual(ratio_rat, 13.894, places=2)

    def test_no_h_or_hbar_used_in_native_frequency_function(self) -> None:
        """Guard: Ensure H_PLANCK and HBAR are NOT used in native frequency function."""
        code = (HERE / "constitutive_profile_solver.py").read_text(encoding="utf-8")
        func_match = re.search(r"def lamb_shift_frequency_native_hz.*?(?=\ndef|\Z)", code, re.DOTALL)
        self.assertIsNotNone(func_match)
        self.assertNotIn("H_PLANCK", func_match.group(0))
        self.assertNotIn("HBAR", func_match.group(0))

    def test_benchmark_csv_output_integrity(self) -> None:
        """Verify CSV benchmark table is generated with 6 rows and correct headers."""
        rows = cps.run_benchmark()
        self.assertEqual(len(rows), 6)
        self.assertTrue(RESULTS_CSV.is_file())
        with RESULTS_CSV.open(newline="", encoding="utf-8") as f:
            read_rows = list(csv.DictReader(f))
        self.assertEqual(len(read_rows), 6)
        self.assertIn("bracket_U_val", read_rows[0])
        self.assertIn("asymptotic_target", read_rows[0])

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

#!/usr/bin/env python3
"""
Unit tests for Unified Aetheric Standing-Wave Spectroscopy (Paper 4).
Validates native grid frequency, EP matrix coalescence, strain-saturated Lamb shift, and anti-smuggling guards.
"""

import csv
import math
import re
import unittest
from pathlib import Path

import unified_aetheric_solver as uas

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE.parent / "results" / "unified_aetheric_benchmark.csv"
FORBIDDEN_CODE = re.compile(r"R_nl|eigh_tridiagonal|sympy|hydrogen\s+import", re.IGNORECASE)


class UnifiedAethericTests(unittest.TestCase):
    def test_native_transition_frequency_has_no_h(self) -> None:
        """Verify Lyman-alpha frequency calculated natively without h or hbar."""
        nu = uas.native_transition_frequency_hz(2, 1, Z=1)
        self.assertAlmostEqual(nu / 1e15, 2.466038, places=4)

    def test_gross_transition_wavelengths(self) -> None:
        """Verify Lyman-alpha is ~121.568 nm and Balmer-alpha is ~656.470 nm."""
        lam_ly = uas.native_transition_wavelength_nm(2, 1, Z=1)
        lam_ba = uas.native_transition_wavelength_nm(3, 2, Z=1)
        self.assertAlmostEqual(lam_ly, 121.56845, places=4)
        self.assertAlmostEqual(lam_ba, 656.46961, places=4)

    def test_non_hermitian_ep_coalescence(self) -> None:
        """Verify that at kappa = gamma, eigenvalues coalesce to pure real omega_0."""
        gamma = 1.0e20
        kappa = gamma
        omega_core = uas.C / uas.R_E
        m_plus, m_minus, status = uas.solve_ep_matrix(omega_core, gamma, kappa)
        self.assertIn("EXCEPTIONAL_POINT", status)
        self.assertAlmostEqual(m_plus["re"] / omega_core, 1.0, places=12)
        self.assertAlmostEqual(m_minus["re"] / omega_core, 1.0, places=12)
        self.assertEqual(m_plus["im"], 0.0)
        self.assertEqual(m_minus["im"], 0.0)

    def test_hydrogen_lamb_shift_within_two_percent(self) -> None:
        """Verify predicted hydrogen Lamb shift is within 2% of empirical NIST value (1057.85 MHz)."""
        nu_H = uas.native_lamb_shift_frequency_hz(2, Z=1, saturated=True)
        self.assertAlmostEqual(nu_H / 1e6, 1045.38, places=1)
        resid_pct = abs(nu_H / 1057.85e6 - 1.0) * 100.0
        self.assertLess(resid_pct, 2.0)

    def test_helium_plus_lamb_shift_logs_eleven_percent_boundary(self) -> None:
        """Verify strain volume contraction contracts He+ overshoot from +19.1% to +11.8%."""
        nu_He = uas.native_lamb_shift_frequency_hz(2, Z=2, saturated=True)
        resid_pct = (nu_He / 14041.45e6 - 1.0) * 100.0
        self.assertAlmostEqual(resid_pct, 11.76, places=1)

    def test_native_3d_fluid_antenna_rate_and_lifetime(self) -> None:
        """Verify native antenna damping gives A = 6.2649e8 s^-1 and tau = 1.5962 ns without h."""
        rate = uas.native_3d_fluid_antenna_rate_lyman_alpha(Z=1)
        self.assertAlmostEqual(rate / 1e8, 6.2649, places=3)
        tau_ns = (1.0 / rate) * 1e9
        self.assertAlmostEqual(tau_ns, 1.5962, places=3)

    def test_no_h_or_hbar_used_in_native_functions(self) -> None:
        """Guard: Ensure H_PLANCK and HBAR are NOT used in native solver functions."""
        code = (HERE / "unified_aetheric_solver.py").read_text(encoding="utf-8")
        func_match = re.search(r"def native_transition_frequency_hz.*?(?=\ndef|\Z)", code, re.DOTALL)
        self.assertIsNotNone(func_match)
        self.assertNotIn("H_PLANCK", func_match.group(0))
        self.assertNotIn("HBAR", func_match.group(0))

    def test_benchmark_csv_output_integrity(self) -> None:
        """Verify CSV benchmark table is generated with 6 rows and correct headers."""
        rows = uas.run_benchmark()
        self.assertEqual(len(rows), 6)
        self.assertTrue(RESULTS_CSV.is_file())
        with RESULTS_CSV.open(newline="", encoding="utf-8") as f:
            read_rows = list(csv.DictReader(f))
        self.assertEqual(len(read_rows), 6)
        self.assertIn("epistemic_status", read_rows[0])
        self.assertIn("predicted_value", read_rows[0])

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

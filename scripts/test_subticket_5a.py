#!/usr/bin/env python3
"""
Unit tests for Sub-Ticket 5A: Circular Ladder 3D Fluid Dipole Antenna Solver.
Validates normalization of nodeless envelopes, NIST agreement across the circular ladder, and code guards.
"""

import csv
import math
import re
import unittest
from pathlib import Path
import numpy as np

import subticket_5a_circular_antenna as s5a

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE.parent / "results" / "circular_ladder_antenna_benchmark.csv"
FORBIDDEN_CODE = re.compile(r"R_nl|eigh_tridiagonal|sympy|hydrogen\s+import", re.IGNORECASE)


class Subticket5ACircularAntennaTests(unittest.TestCase):
    def test_circular_envelopes_are_unit_normalized(self) -> None:
        """Verify integral_0^inf r^2 * R_n(r)^2 dr == 1.0 to within 1e-6 across n = 1..6."""
        for n_val in (1, 2, 3, 4, 5, 6):
            R_n = s5a.nodeless_circular_envelope(n_val, s5a.R_GRID, Z=1)
            norm_val = s5a.trapz((s5a.R_GRID ** 2) * (R_n ** 2), s5a.R_GRID)
            self.assertAlmostEqual(norm_val, 1.0, places=5)

    def test_all_five_circular_transitions_agree_with_nist_to_twenty_ppm(self) -> None:
        """Verify all 5 circular ladder transitions (2p->1s through 6h->5g) agree with NIST to <= 0.002%."""
        rows = s5a.run_benchmark()
        self.assertEqual(len(rows), 5)
        for r in rows:
            resid_pct = abs(float(r["residual_pct"].rstrip(" %")))
            self.assertLessEqual(resid_pct, 0.0020, f"Failed for {r['transition']}: {resid_pct}%")

    def test_lyman_alpha_rate_matches_native_closed_form(self) -> None:
        """Verify 2p -> 1s rate matches (2/3)^8 * 4*pi*mu*alpha^6 / (e^2 * mu_0^1.5 * eps_0^0.5)."""
        A_calc, tau_ns, _ = s5a.circular_dipole_antenna_rate_s(2, 1, Z=1)
        # Expected = 6.2649e8 s^-1
        self.assertAlmostEqual(A_calc / 1e8, 6.2649, places=3)
        self.assertAlmostEqual(tau_ns, 1.596, places=2)

    def test_no_h_or_hbar_used_in_native_frequency_function(self) -> None:
        """Guard: Ensure H_PLANCK and HBAR are NOT used in native frequency function."""
        code = (HERE / "subticket_5a_circular_antenna.py").read_text(encoding="utf-8")
        func_match = re.search(r"def native_transition_frequency_hz.*?(?=\ndef|\Z)", code, re.DOTALL)
        self.assertIsNotNone(func_match)
        self.assertNotIn("H_PLANCK", func_match.group(0))
        self.assertNotIn("HBAR", func_match.group(0))

    def test_benchmark_csv_output_integrity(self) -> None:
        """Verify CSV benchmark table is generated with 5 rows and correct headers."""
        self.assertTrue(RESULTS_CSV.is_file())
        with RESULTS_CSV.open(newline="", encoding="utf-8") as f:
            read_rows = list(csv.DictReader(f))
        self.assertEqual(len(read_rows), 5)
        self.assertIn("predicted_A_s", read_rows[0])
        self.assertIn("nist_observed_A_s", read_rows[0])
        self.assertIn("overlap_integral_a_mu", read_rows[0])

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

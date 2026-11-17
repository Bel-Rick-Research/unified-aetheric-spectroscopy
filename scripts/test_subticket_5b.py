#!/usr/bin/env python3
"""
Unit tests for Sub-Ticket 5B: Single-Node Radial Ripples (n_r = 1) 3D Fluid Dipole Antenna Solver.
Validates exact nodal radius, unit normalization, mutual orthogonality, phase cancellation, and NIST agreement.
"""

import csv
import math
import re
import unittest
from pathlib import Path
import numpy as np

import subticket_5b_radial_ripples as s5b

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE.parent / "results" / "radial_ripples_antenna_benchmark.csv"
FORBIDDEN_CODE = re.compile(r"R_nl|eigh_tridiagonal|sympy|hydrogen\s+import", re.IGNORECASE)


class Subticket5BRadialRipplesTests(unittest.TestCase):
    def test_nodal_radius_matches_theoretical_sturm_liouville_ode_root(self) -> None:
        """Verify r_node = n * (n - 1) * a_mu gives 2*a_mu for 2s, 6*a_mu for 3p, 12*a_mu for 4d."""
        self.assertAlmostEqual(s5b.nodal_radius_m(2) / s5b.A_MU, 2.0, places=12)
        self.assertAlmostEqual(s5b.nodal_radius_m(3) / s5b.A_MU, 6.0, places=12)
        self.assertAlmostEqual(s5b.nodal_radius_m(4) / s5b.A_MU, 12.0, places=12)

    def test_single_node_envelopes_are_unit_normalized(self) -> None:
        """Verify integral_0^inf r^2 * R_nl(r)^2 dr == 1.0 to within 1e-5 for 2s, 3p, 4d."""
        for n_val, l_val in ((2, 0), (3, 1), (4, 2)):
            R_nl = s5b.fluid_acoustic_envelope(n_val, l_val, s5b.R_GRID, Z=1)
            norm_val = s5b.trapz((s5b.R_GRID ** 2) * (R_nl ** 2), s5b.R_GRID)
            self.assertAlmostEqual(norm_val, 1.0, places=4)

    def test_mutual_orthogonality_of_sturm_liouville_fluid_modes(self) -> None:
        """Verify <1s|2s>, <2p|3p>, and <3d|4d> overlap integrals vanish identically (<= 1e-12)."""
        R_1s = s5b.fluid_acoustic_envelope(1, 0, s5b.R_GRID, Z=1)
        R_2s = s5b.fluid_acoustic_envelope(2, 0, s5b.R_GRID, Z=1)
        ortho_s = abs(s5b.trapz((s5b.R_GRID ** 2) * R_1s * R_2s, s5b.R_GRID))
        self.assertLess(ortho_s, 1e-12)

        R_2p = s5b.fluid_acoustic_envelope(2, 1, s5b.R_GRID, Z=1)
        R_3p = s5b.fluid_acoustic_envelope(3, 1, s5b.R_GRID, Z=1)
        ortho_p = abs(s5b.trapz((s5b.R_GRID ** 2) * R_2p * R_3p, s5b.R_GRID))
        self.assertLess(ortho_p, 1e-12)

        R_3d = s5b.fluid_acoustic_envelope(3, 2, s5b.R_GRID, Z=1)
        R_4d = s5b.fluid_acoustic_envelope(4, 2, s5b.R_GRID, Z=1)
        ortho_d = abs(s5b.trapz((s5b.R_GRID ** 2) * R_3d * R_4d, s5b.R_GRID))
        self.assertLess(ortho_d, 1e-12)

    def test_phase_reversal_across_radial_node(self) -> None:
        """Verify 3p fluid envelope reverses phase (+ to -) exactly across r_node = 6 * a_mu."""
        R_3p = s5b.fluid_acoustic_envelope(3, 1, s5b.R_GRID, Z=1)
        idx_inner = int(np.searchsorted(s5b.R_GRID, 3.0 * s5b.A_MU))
        idx_outer = int(np.searchsorted(s5b.R_GRID, 9.0 * s5b.A_MU))
        self.assertGreater(R_3p[idx_inner], 0.0, "Inner lobe must be positive")
        self.assertLess(R_3p[idx_outer], 0.0, "Outer lobe must be negative")

    def test_all_three_single_node_transitions_agree_with_nist_to_twenty_ppm(self) -> None:
        """Verify 3p->1s, 3p->2s, and 4d->2p agree with NIST to <= 0.002% (20 ppm)."""
        rows = s5b.run_benchmark()
        self.assertEqual(len(rows), 3)
        for r in rows:
            resid_pct = abs(float(r["residual_pct"].rstrip(" %")))
            self.assertLessEqual(resid_pct, 0.0020, f"Failed for {r['transition']}: {resid_pct}%")

    def test_no_h_or_hbar_used_in_native_frequency_function(self) -> None:
        """Guard: Ensure H_PLANCK and HBAR are NOT used in native frequency function."""
        code = (HERE / "subticket_5b_radial_ripples.py").read_text(encoding="utf-8")
        func_match = re.search(r"def native_transition_frequency_hz.*?(?=\ndef|\Z)", code, re.DOTALL)
        self.assertIsNotNone(func_match)
        self.assertNotIn("H_PLANCK", func_match.group(0))
        self.assertNotIn("HBAR", func_match.group(0))

    def test_benchmark_csv_output_integrity(self) -> None:
        """Verify CSV benchmark table is generated with 3 rows and correct headers."""
        self.assertTrue(RESULTS_CSV.is_file())
        with RESULTS_CSV.open(newline="", encoding="utf-8") as f:
            read_rows = list(csv.DictReader(f))
        self.assertEqual(len(read_rows), 3)
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

#!/usr/bin/env python3
"""
Unit tests for Sub-Ticket 5C: Full 55-Line Catalog Sweep & TRK Sum Rule.

Validates:
1. Exactly 55 dipole transitions evaluated for n <= 6.
2. Unit normalization across all 21 spatial modes up to n = 6.
3. Mutual cavity mode orthogonality across distinct radial harmonics.
4. Agreement with NIST ASD across all 55 transitions to <= 0.02% (200 ppm).
5. Exact consistency with Sub-Ticket 5A (circular) and Sub-Ticket 5B (single-node).
6. TRK oscillator strength conservation (1s -> np discrete sum = 0.5460).
7. Benchmark CSV output integrity (55 rows, non-empty, proper headers).
"""

import csv
import math
import unittest
from pathlib import Path
import numpy as np

import subticket_5c_full_catalog_sweep as s5c

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"


class TestSubTicket5C(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modes = s5c.precompute_cavity_modes(n_max=6, Z=1)
        cls.rows = s5c.run_benchmark()

    def test_55_lines_count(self):
        """Verify exactly 55 allowed dipole transitions exist for n <= 6."""
        self.assertEqual(len(self.rows), 55)

    def test_all_21_modes_unit_normalized(self):
        """Verify all 21 fluid acoustic modes up to n=6 are unit-normalized."""
        r_grid = s5c.R_GRID
        trapz = s5c.trapz
        for (n, l), R_arr in self.modes.items():
            norm_sq = trapz((r_grid ** 2) * (R_arr ** 2), r_grid)
            self.assertAlmostEqual(norm_sq, 1.0, places=5, msg=f"Mode ({n},{l}) norm was {norm_sq}")

    def test_mutual_mode_orthogonality(self):
        """Verify distinct radial modes with same l are mutually orthogonal."""
        r_grid = s5c.R_GRID
        trapz = s5c.trapz
        # Test (1s, 2s), (1s, 3s), (2s, 3s), (2p, 3p), (3d, 4d)
        pairs = [
            ((1, 0), (2, 0)),
            ((1, 0), (3, 0)),
            ((2, 0), (3, 0)),
            ((2, 1), (3, 1)),
            ((3, 2), (4, 2)),
        ]
        for m1, m2 in pairs:
            overlap = trapz((r_grid ** 2) * self.modes[m1] * self.modes[m2], r_grid)
            self.assertLess(abs(overlap), 1e-10, msg=f"Modes {m1} and {m2} not orthogonal: {overlap}")

    def test_frobenius_nodal_zero_crossings(self):
        """Verify Frobenius acoustic polynomial roots match physical ODE zero-crossings."""
        r_grid = s5c.R_GRID
        a_mu = s5c.A_MU

        # 2s (n=2, l=0, nr=1): node at r = 2.0 * a_mu
        rho_2s = 2.0 * r_grid / (2.0 * a_mu)
        w_2s = s5c.frobenius_acoustic_polynomial(1, 0, rho_2s)
        zero_idx_2s = np.where(np.diff(np.sign(w_2s)))[0][0]
        r_zero_2s = r_grid[zero_idx_2s] / a_mu
        self.assertAlmostEqual(r_zero_2s, 2.0, places=2)

        # 3p (n=3, l=1, nr=1): node at r = 6.0 * a_mu
        rho_3p = 2.0 * r_grid / (3.0 * a_mu)
        w_3p = s5c.frobenius_acoustic_polynomial(1, 1, rho_3p)
        zero_idx_3p = np.where(np.diff(np.sign(w_3p)))[0][0]
        r_zero_3p = r_grid[zero_idx_3p] / a_mu
        self.assertAlmostEqual(r_zero_3p, 6.0, places=2)

    def test_nist_benchmark_residuals_bounded(self):
        """Verify all 55 transitions match NIST ASD to within <= 0.02% (200 ppm)."""
        residuals = [abs(r["residual_pct"]) for r in self.rows if not math.isnan(r["residual_pct"])]
        self.assertEqual(len(residuals), 55)
        max_res = max(residuals)
        mean_res = sum(residuals) / len(residuals)
        self.assertLess(max_res, 0.02, f"Max residual {max_res:.4f}% exceeded 0.02% threshold")
        self.assertLess(mean_res, 0.01, f"Mean residual {mean_res:.4f}% exceeded 0.01% threshold")

    def test_circular_ladder_exact_consistency(self):
        """Verify 5 circular ladder transitions match Sub-Ticket 5A benchmark."""
        circular_map = {
            "2p -> 1s": 6.2649e8,
            "3d -> 2p": 6.4651e7,
            "4f -> 3d": 1.3788e7,
            "5g -> 4f": 4.2542e6,
            "6h -> 5g": 1.6448e6,
        }
        for row in self.rows:
            trans = row["transition"]
            if trans in circular_map:
                expected = circular_map[trans]
                actual = row["A_predicted_s_inv"]
                rel_diff = abs(actual - expected) / expected
                self.assertLess(rel_diff, 1e-4, f"Mismatch on {trans}: actual={actual}, expected={expected}")

    def test_single_node_exact_consistency(self):
        """Verify single-node transitions match Sub-Ticket 5B benchmark."""
        single_node_map = {
            "3p -> 1s": 1.6725e8,
            "3p -> 2s": 2.2448e7,
            "4d -> 2p": 2.0625e7,
        }
        for row in self.rows:
            trans = row["transition"]
            if trans in single_node_map:
                expected = single_node_map[trans]
                actual = row["A_predicted_s_inv"]
                rel_diff = abs(actual - expected) / expected
                self.assertLess(rel_diff, 1e-4, f"Mismatch on {trans}: actual={actual}, expected={expected}")

    def test_trk_sum_rule_conservation(self):
        """Verify Thomas-Reiche-Kuhn sum rule for 1s -> np bound states."""
        trk = s5c.verify_trk_sum_rule(self.modes)
        sum_1s = trk["sum_1s_to_np_n6"]
        # Exact theoretical sum of discrete lines n=2..6 is 0.546123
        self.assertAlmostEqual(sum_1s, 0.5460, places=3)

    def test_csv_output_file_integrity(self):
        """Verify full_catalog_55_lines_benchmark.csv exists and has 55 data rows."""
        csv_file = RESULTS / "full_catalog_55_lines_benchmark.csv"
        self.assertTrue(csv_file.exists())
        with csv_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            data_rows = list(reader)
        self.assertEqual(len(data_rows), 55)
        self.assertIn("transition", data_rows[0])
        self.assertIn("overlap_I_ul_a_mu", data_rows[0])
        self.assertIn("A_predicted_s_inv", data_rows[0])
        self.assertIn("A_nist_s_inv", data_rows[0])


if __name__ == "__main__":
    unittest.main()

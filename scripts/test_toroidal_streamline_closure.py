#!/usr/bin/env python3
"""
Unit tests for Toroidal Recirculating Streamline Contours & Vortex Closure Solver (TICKET-02).
Validates Stokes streamfunction symmetry, Bernoulli pressure tube, aspect ratio 1/alpha^2,
self-induced propagation speed, and AST anti-smuggling guards.
"""

import csv
import math
import re
import unittest
from pathlib import Path

import toroidal_streamline_closure_solver as tsc

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE.parent / "results" / "toroidal_streamline_closure_benchmark.csv"
FORBIDDEN_CODE = re.compile(r"R_nl|eigh_tridiagonal|sympy|hydrogen\s+import", re.IGNORECASE)


class ToroidalStreamlineClosureTests(unittest.TestCase):
    def test_dipole_streamfunction_symmetry(self) -> None:
        """Verify Stokes streamfunction for coaxial source-sink pair is symmetric in z: psi(varpi, -z) == psi(varpi, z)."""
        for z in (0.1 * tsc.A_MU, 0.5 * tsc.A_MU, 1.2 * tsc.A_MU):
            psi_pos = tsc.dipole_stokes_streamfunction(tsc.A_MU, z)
            psi_neg = tsc.dipole_stokes_streamfunction(tsc.A_MU, -z)
            self.assertAlmostEqual(psi_pos, psi_neg, places=12)

    def test_bernoulli_suction_tube_minimum_pressure(self) -> None:
        """Verify that static pressure along the coaxial midpoint tube is lower than at the exterior flank."""
        v_mid_w, v_mid_z = tsc.dipole_velocity_field(varpi=tsc.R_E, z=0.0)
        v_ext_w, v_ext_z = tsc.dipole_velocity_field(varpi=3.0 * tsc.A_MU, z=0.0)
        v_mid_mag = math.sqrt(v_mid_w**2 + v_mid_z**2)
        v_ext_mag = math.sqrt(v_ext_w**2 + v_ext_z**2)
        self.assertGreater(v_mid_mag, v_ext_mag)

    def test_aspect_ratio_matches_inverse_alpha_squared(self) -> None:
        """Verify toroidal vortex aspect ratio R_0 / r_0 equals 1 / alpha^2 (~ 18779)."""
        aspect_ratio = tsc.A_MU / tsc.R_E
        expected = 1.0 / (tsc.ALPHA ** 2)
        self.assertAlmostEqual(aspect_ratio / expected, 1.0, places=10)

    def test_vortex_ring_self_induced_velocity_helmholtz_lamb(self) -> None:
        """Verify thin-core vortex ring self-induced speed matches classical Helmholtz-Lamb formula."""
        u_ring = tsc.vortex_ring_self_induced_velocity_m_s(tsc.A_MU, tsc.R_E, tsc.GAMMA_0)
        expected = (tsc.GAMMA_0 / (4.0 * math.pi * tsc.A_MU)) * (math.log(8.0 * tsc.A_MU / tsc.R_E) - 0.25)
        self.assertAlmostEqual(u_ring, expected, places=10)
        self.assertGreater(u_ring, 0.0)

    def test_benchmark_csv_output_integrity(self) -> None:
        """Verify CSV benchmark table is generated with 7 rows and correct headers."""
        rows = tsc.run_benchmark()
        self.assertEqual(len(rows), 7)
        self.assertTrue(RESULTS_CSV.is_file())
        with RESULTS_CSV.open(newline="", encoding="utf-8") as f:
            read_rows = list(csv.DictReader(f))
        self.assertEqual(len(read_rows), 7)
        self.assertIn("physical_condition", read_rows[0])
        self.assertIn("bernoulli_pressure_Pa", read_rows[0])

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

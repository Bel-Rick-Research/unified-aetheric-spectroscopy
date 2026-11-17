#!/usr/bin/env python3
"""
Unit tests for Bernoulli Source-Sink Suction & Neutron n=0 Ground State Solver.
Validates force balance, 1/r^3 repulsive barrier, n=0 inertia damping, and electric neutrality.
"""

import csv
import math
import re
import unittest
from pathlib import Path

import bernoulli_neutron_solver as bns

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE.parent / "results" / "bernoulli_neutron_benchmark.csv"
FORBIDDEN_CODE = re.compile(r"R_nl|eigh_tridiagonal|sympy|hydrogen\s+import", re.IGNORECASE)


class BernoulliNeutronTests(unittest.TestCase):
    def test_bernoulli_force_equals_coulomb_in_magnitude(self) -> None:
        """Verify Bernoulli suction force matches standard e^2 / (4*pi*eps0*d^2)."""
        d = bns.A_MU
        f_bern = bns.bernoulli_attraction_force_N(d, Z=1)
        expected = -bns.E_CHARGE**2 / (4.0 * math.pi * bns.EPS_0 * d**2)
        self.assertAlmostEqual(f_bern / expected, 1.0, places=12)

    def test_free_space_equilibrium_at_bohr_radius(self) -> None:
        """Verify net force F_Bernoulli + F_inertia is exactly zero at d = a_mu for n=1."""
        d = bns.A_MU
        f_net = bns.effective_force_N(d, n=1, Z=1)
        f_bern = abs(bns.bernoulli_attraction_force_N(d, Z=1))
        # Relative residual should be near machine epsilon
        self.assertAlmostEqual(f_net / f_bern, 0.0, places=14)

    def test_repulsive_barrier_at_sub_bohr_distances(self) -> None:
        """Verify 1/d^3 inertia exceeds 1/d^2 Bernoulli suction at d < a_mu, preventing collapse."""
        for factor in (0.1, 0.25, 0.5, 0.8):
            d = factor * bns.A_MU
            f_net = bns.effective_force_N(d, n=1, Z=1)
            self.assertGreater(f_net, 0.0, f"Expected outward repulsive force at d={d}")

    def test_nuclear_inertia_damping_collapses_to_n0_core(self) -> None:
        """Verify that when v_theta is damped to 0 (n=0), F_inertia=0 and Bernoulli suction pulls sink into core."""
        d_core = bns.R_E
        f_iner = bns.centrifugal_lattice_inertia_force_N(d_core, n=0)
        self.assertEqual(f_iner, 0.0)
        f_net = bns.effective_force_N(d_core, n=0, Z=1)
        self.assertLess(f_net, 0.0, "Expected net inward suction at n=0")
        self.assertAlmostEqual(f_net, bns.bernoulli_attraction_force_N(d_core, Z=1), places=12)

    def test_neutron_exterior_flux_divergence_is_identically_zero(self) -> None:
        """Verify that coaxial source (+Q) and sink (-Q) produce zero net exterior divergence (neutrality)."""
        div_flux = bns.net_exterior_flux_divergence(r=1.0e-10, d=bns.R_E, Q=1.0)
        self.assertEqual(div_flux, 0.0)

    def test_benchmark_csv_output_integrity(self) -> None:
        """Verify CSV benchmark table is generated with 5 rows and correct headers."""
        rows = bns.run_benchmark()
        self.assertEqual(len(rows), 5)
        self.assertTrue(RESULTS_CSV.is_file())
        with RESULTS_CSV.open(newline="", encoding="utf-8") as f:
            read_rows = list(csv.DictReader(f))
        self.assertEqual(len(read_rows), 5)
        self.assertIn("physical_condition", read_rows[0])
        self.assertIn("bernoulli_suction_N", read_rows[0])

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

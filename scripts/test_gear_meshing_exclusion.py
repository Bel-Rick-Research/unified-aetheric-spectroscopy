#!/usr/bin/env python3
"""
Unit tests for Hydrodynamic Gear-Meshing & Chirality Exclusion Solver (TICKET-06).
Validates spatial volume conflict, chiral phase-locking, antimatter annihilation, and 2n^2 shell capacity.
"""

import csv
import math
import re
import unittest
from pathlib import Path

import gear_meshing_exclusion_solver as gms

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE.parent / "results" / "gear_meshing_exclusion_benchmark.csv"
FORBIDDEN_CODE = re.compile(r"R_nl|eigh_tridiagonal|sympy|hydrogen\s+import", re.IGNORECASE)


class GearMeshingExclusionTests(unittest.TestCase):
    def test_identical_chirality_generates_repulsive_stagnation_pressure(self) -> None:
        """Verify identical chirality vortex rings produce head-on collision and positive stagnation pressure spike."""
        s1 = gms.ChiralVortexState("e1", -1, +1, +1)
        s2 = gms.ChiralVortexState("e2", -1, +1, +1)
        res = gms.evaluate_vortex_coupling(s1, s2, n=1, Z=1)
        self.assertFalse(res["is_stable"])
        self.assertEqual(res["coupling_type"], "IDENTICAL_CHIRALITY_COLLISION")
        self.assertIn("FORBIDDEN", res["stability_status"])
        p_val = float(res["stagnation_pressure_Pa"].split()[0])
        self.assertGreater(p_val, 0.0)
        self.assertAlmostEqual(p_val, 4.67e12, delta=0.05e12)
        p_native = gms.native_cavity_stagnation_pressure(n=1, Z=1)
        self.assertAlmostEqual(p_native, 4.6723e12, delta=0.01e12)

    def test_complementary_torsion_produces_laminar_gear_meshing(self) -> None:
        """Verify complementary torsion spins (+1 and -1) mesh with zero stagnation pressure and net zero J."""
        s_up = gms.ChiralVortexState("e_up", -1, +1, +1)
        s_down = gms.ChiralVortexState("e_down", -1, +1, -1)
        res = gms.evaluate_vortex_coupling(s_up, s_down, n=1, Z=2)
        self.assertTrue(res["is_stable"])
        self.assertEqual(res["coupling_type"], "GEAR_MESHED_LAMINAR_LOCK")
        self.assertIn("STABLE", res["stability_status"])
        self.assertIn("0.0000", res["stagnation_pressure_Pa"])
        self.assertIn("0.0", res["net_angular_momentum"])

    def test_total_3mode_inversion_annihilates_and_releases_1022_kev(self) -> None:
        """Verify total inversion across radial, toroidal, and torsion modes triggers annihilation releasing 2*m_e*c^2."""
        e_minus = gms.ChiralVortexState("e-", -1, +1, +1)
        e_plus = gms.ChiralVortexState("e+", +1, -1, -1)
        res = gms.evaluate_vortex_coupling(e_minus, e_plus, n=1, Z=1)
        self.assertFalse(res["is_stable"])
        self.assertEqual(res["coupling_type"], "ANTIMATTER_ANNIHILATION")
        self.assertIn("ANNIHILATED", res["stability_status"])
        self.assertIn("1022.0 keV", res["stability_status"])

    def test_shell_capacity_formula_2n_squared(self) -> None:
        """Verify shell capacity N_max(n) = 2 * n^2 gives 2, 8, 18, 32 for shells n=1, 2, 3, 4."""
        self.assertEqual(gms.shell_capacity(1), 2)
        self.assertEqual(gms.shell_capacity(2), 8)
        self.assertEqual(gms.shell_capacity(3), 18)
        self.assertEqual(gms.shell_capacity(4), 32)

    def test_benchmark_csv_output_integrity(self) -> None:
        """Verify CSV benchmark table is generated with 7 rows and correct headers."""
        rows = gms.run_benchmark()
        self.assertEqual(len(rows), 7)
        self.assertTrue(RESULTS_CSV.is_file())
        with RESULTS_CSV.open(newline="", encoding="utf-8") as f:
            read_rows = list(csv.DictReader(f))
        self.assertEqual(len(read_rows), 7)
        self.assertIn("coupling_mechanism", read_rows[0])
        self.assertIn("stability_result", read_rows[0])

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

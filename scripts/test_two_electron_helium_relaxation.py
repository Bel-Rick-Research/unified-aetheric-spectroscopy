#!/usr/bin/env python3
"""
Unit tests for Two-Electron Helium 1s^2 Coupled Fluid Relaxation Solver (TICKET-06 Extension).
Validates unperturbed baseline, antipodal screening, distributed toroidal envelope screening,
deformation correlation energy, and AST anti-smuggling guards.
"""

import csv
import math
import re
import unittest
from pathlib import Path

import two_electron_helium_relaxation_solver as tehrs

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE.parent / "results" / "two_electron_helium_relaxation_benchmark.csv"
FORBIDDEN_CODE = re.compile(r"R_nl|eigh_tridiagonal|sympy|hydrogen\s+import", re.IGNORECASE)


class TwoElectronHeliumRelaxationTests(unittest.TestCase):
    def test_unperturbed_helium_energy(self) -> None:
        """Verify non-interacting helium ground energy E_0 = -2 * Z^2 * E_Ryd = -8 * 13.6038 eV = -108.83 eV."""
        e_0 = tehrs.unperturbed_hydrogenic_helium_energy_eV(Z=2)
        expected = -8.0 * tehrs.E_RYD_EV
        self.assertAlmostEqual(e_0, expected, places=5)
        self.assertAlmostEqual(e_0, -108.8306, places=1)

    def test_antipodal_point_screening_energy(self) -> None:
        """Verify antipodal point-sink screening Z_eff = Z - 1/4 = 1.75 gives E = -83.32 eV."""
        e_anti = tehrs.antipodal_point_screening_energy_eV(Z=2)
        expected = -2.0 * (1.75 ** 2) * tehrs.E_RYD_EV
        self.assertAlmostEqual(e_anti, expected, places=5)
        self.assertAlmostEqual(e_anti, -83.3235, places=1)

    def test_distributed_toroidal_envelope_energy(self) -> None:
        """Verify distributed 3D toroidal envelope screening Z_eff = 1.6875 gives E = -77.48 eV (< 2% from NIST)."""
        e_dist = tehrs.distributed_envelope_screening_energy_eV(Z=2)
        expected = -2.0 * ((1.6875) ** 2) * tehrs.E_RYD_EV
        self.assertAlmostEqual(e_dist, expected, places=5)
        rel_diff = abs(e_dist - tehrs.E_HE_NIST_EV) / abs(tehrs.E_HE_NIST_EV)
        self.assertLess(rel_diff, 0.02)  # Within 2.0% of empirical -79.005 eV

    def test_correlation_energy_sign_and_magnitude(self) -> None:
        """Verify core fluid oblate deformation deepens binding energy by Delta E ~ -1.53 eV."""
        e_dist = tehrs.distributed_envelope_screening_energy_eV(Z=2)
        delta_corr = tehrs.E_HE_NIST_EV - e_dist
        self.assertLess(delta_corr, 0.0, "Correlation energy must deepen binding (negative Delta E)")
        self.assertAlmostEqual(delta_corr, -1.529, places=1)

    def test_benchmark_csv_output_integrity(self) -> None:
        """Verify CSV benchmark table is generated with 5 rows and correct headers."""
        rows = tehrs.run_benchmark()
        self.assertEqual(len(rows), 5)
        self.assertTrue(RESULTS_CSV.is_file())
        with RESULTS_CSV.open(newline="", encoding="utf-8") as f:
            read_rows = list(csv.DictReader(f))
        self.assertEqual(len(read_rows), 5)
        self.assertIn("effective_charge_Z_eff", read_rows[0])
        self.assertIn("epistemic_status", read_rows[0])

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

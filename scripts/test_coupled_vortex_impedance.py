#!/usr/bin/env python3
"""
Unit tests for Coupled Vortex Impedance & Reduced Mass Solver (TICKET-10).
Validates Kelvin impulse conservation, series acoustic impedance reduction,
geometric 6*pi^5 agreement with CODATA, and anti-smuggling guards.
"""

import csv
import math
import re
import unittest
from pathlib import Path

import coupled_vortex_impedance_solver as cvis

HERE = Path(__file__).resolve().parent
RESULTS_CSV = HERE.parent / "results" / "coupled_vortex_impedance_benchmark.csv"
FORBIDDEN_CODE = re.compile(r"R_nl|eigh_tridiagonal|sympy|hydrogen\s+import", re.IGNORECASE)


class CoupledVortexImpedanceTests(unittest.TestCase):
    def test_kelvin_impulse_conservation(self) -> None:
        """Verify center-of-vorticity relative motion acceleration is scaled by 1/mu."""
        m_e = cvis.M_E_KG
        m_p = cvis.M_P_KG
        mu = cvis.series_impedance_reduced_mass(m_e, m_p)
        # Acceleration relation: d^2(r)/dt^2 = F/m_e - (-F/m_p) = F*(1/m_e + 1/m_p) = F/mu
        inv_mu = (1.0 / m_e) + (1.0 / m_p)
        self.assertAlmostEqual((1.0 / mu) / inv_mu, 1.0, places=14)

    def test_series_impedance_reduces_to_mu(self) -> None:
        """Verify series reactive impedance Z_eff = (Z_1 * Z_2)/(Z_1 + Z_2) equals i*omega*mu."""
        m_e = 1.0
        m_p = 1836.15267344
        mu = cvis.series_impedance_reduced_mass(m_e, m_p)
        expected = (m_e * m_p) / (m_e + m_p)
        self.assertAlmostEqual(mu, expected, places=12)

    def test_hydrogen_reduced_mass_agreement_with_codata(self) -> None:
        """Verify geometric 6*pi^5 reduced mass matches CODATA to within 0.015 ppm."""
        comp = cvis.hydrogen_reduced_mass_comparison()
        self.assertAlmostEqual(comp["mu_me_geom"], 0.9994556692, places=8)
        self.assertAlmostEqual(comp["mu_me_codata"], 0.9994556794, places=8)
        self.assertLess(comp["residual_ppm"], 0.015)
        self.assertLess(comp["absolute_diff"], 2e-8)

    def test_positronium_symmetric_halving(self) -> None:
        """Verify symmetric gear-meshed vortex pair (e+ and e-) halves effective inertia to mu = m_e / 2."""
        mu_ps = cvis.series_impedance_reduced_mass(cvis.M_E_KG, cvis.M_E_KG)
        self.assertEqual(mu_ps, 0.5 * cvis.M_E_KG)

    def test_deuterium_isotope_shift(self) -> None:
        """Verify Deuterium mass loading produces ~272 ppm isotope shift."""
        cat = cvis.coupled_vortex_systems_catalog()
        shift_ppm = cat["deuterium"]["isotope_shift_ppm"]
        self.assertGreater(shift_ppm, 270.0)
        self.assertLess(shift_ppm, 275.0)

    def test_finite_size_vortex_quadrupole_bound(self) -> None:
        """Verify vortex core throat r_e = alpha^2 * a_mu restricts quadrupole distortion to < 2.0 ppb."""
        fs = cvis.finite_size_vortex_multipole_limit()
        self.assertLess(fs["quadrupole_ppb"], 2.0)
        self.assertAlmostEqual(fs["quadrupole_ppb"], 1.418, places=2)

    def test_benchmark_csv_output_integrity(self) -> None:
        """Verify CSV benchmark table is generated with 6 rows and correct headers."""
        rows = cvis.run_benchmark()
        self.assertEqual(len(rows), 6)
        self.assertTrue(RESULTS_CSV.is_file())
        with RESULTS_CSV.open(newline="", encoding="utf-8") as f:
            read_rows = list(csv.DictReader(f))
        self.assertEqual(len(read_rows), 6)
        self.assertIn("aspect", read_rows[0])
        self.assertIn("epistemic_status", read_rows[0])
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

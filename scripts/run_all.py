#!/usr/bin/env python3
"""
One-command verification for Unified Aetheric Standing-Wave Spectroscopy (Paper 4).

    python3 run_all.py                    verify recorded SHA-256 manifest and run all unit tests
    python3 run_all.py --update-manifest  re-record manifest and run tests (after intended change)
"""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main(update_manifest: bool) -> int:
    print("=== Unified Aetheric Standing-Wave Spectroscopy (Paper 4): Verification ===")
    import generate_manifest as gm
    import unified_aetheric_solver as uas
    import bernoulli_neutron_solver as bns

    print("\n1. Regenerating Benchmarks")
    rows = uas.run_benchmark()
    uas.print_summary(rows)

    rows_bns = bns.run_benchmark()
    bns.print_summary(rows_bns)

    import mercury_stress_precession_solver as msps
    rows_msps = msps.run_benchmark()
    msps.print_summary(rows_msps)

    import constitutive_profile_solver as cps
    rows_cps = cps.run_benchmark()
    cps.print_summary(rows_cps)

    import gear_meshing_exclusion_solver as gms
    rows_gms = gms.run_benchmark()
    gms.print_summary(rows_gms)

    print("\n2. Manifest Verification")
    if update_manifest:
        count = gm.generate_manifest()
        print(f"  Re-recorded {count} entries into MANIFEST.sha256")
    else:
        problems = gm.verify_manifest()
        if problems:
            print("  MANIFEST MISMATCH:\n    " + "\n    ".join(problems))
            print("  (run with --update-manifest only if the change was intended)")
            return 1
        print("  OK: All data, scripts and results match recorded SHA-256 hashes")

    print("\n3. Unit Tests")
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print(f"\nRESULT: All checks passed ({result.testsRun} unit tests).")
        return 0
    else:
        print(f"\nRESULT: FAILED ({len(result.failures)} failures, {len(result.errors)} errors).")
        return 1


if __name__ == "__main__":
    sys.exit(main("--update-manifest" in sys.argv))

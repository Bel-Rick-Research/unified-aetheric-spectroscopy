#!/usr/bin/env python3
"""
Hydrodynamic Constitutive Profile & Dielectric Grid Saturation Solver (TICKET-04).

Models:
1. Rational Fluid Continuity Transition Function:
       T(r) = R_trans / (R_trans + r)
   Replacing statistical plasma Debye screening with pure geometric fluid continuity:
   - Core limit (r << R_trans): r^2 * K^2(r) ~ (2Z / a_mu) * r  => Quadratic shells r_n = n^2 * a_mu / Z
   - Bulk limit (r >> R_trans): r^2 * K^2(r) -> (2Z * R_trans / a_mu) = g_0 = const => Euler-Cauchy r_n = r_0 * k^n
2. Non-Linear Equation of State and Lattice Elasticity:
   - Medium bulk modulus: K_A = rho_A * c^2 ~ 0.90 Pa
   - Inflow density perturbation: Delta rho_A / rho_A = -0.5 * (v/c)^2
   - Dielectric strain volume integral:
         S(n, Z) = integral_{r_e}^{r_n} dr / r = ln(r_n / r_e) = ln(n^2 / (Z * alpha^2))
   - Geometric strain saturation factor:
         eta_strain(n, Z) = ln(n^2 / (Z * alpha^2)) / ln(4 / alpha^2)
   - Contracts He+/H Lamb ratio from raw 16.0 down to 15.012 (+11.8% residual).
   - Remaining +11.8% is the explicit non-linear lattice elasticity boundary (bulk modulus saturation).

Writes results/constitutive_profile_benchmark.csv
"""

import csv
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"

# Fundamental Dielectric Lattice Constants (CODATA 2018 / SI 2019)
C = 299792458.0                  # Transverse grid wave speed (m/s)
E_CHARGE = 1.602176634e-19       # Elementary charge (C)
EPS_0 = 8.8541878128e-12         # Grid permittivity (F/m)
MU_0 = 1.0 / (EPS_0 * C**2)       # Grid permeability (H/m)
M_E = 9.1093837015e-31           # Electron mass (kg)
M_P = 1.67262192369e-27          # Proton mass (kg)
MU_H = M_E * M_P / (M_E + M_P)   # Two-body reduced mass (kg)

Z_0 = math.sqrt(MU_0 / EPS_0)
H_PLANCK = 6.62607015e-34
HBAR = H_PLANCK / (2.0 * math.pi)
ALPHA = E_CHARGE**2 * Z_0 / (4.0 * math.pi * HBAR)

R_E = MU_0 * E_CHARGE**2 / (4.0 * math.pi * MU_H)   # Core radius ~ 2.8195e-15 m
A_MU = R_E / (ALPHA ** 2)                           # Reduced-mass Bohr radius ~ 5.2946e-11 m
R_TRANS_M = 1.0e-3                                  # Hydrodynamic transition radius (1 mm)

# Native Lamb prefactor: Delta nu_0 = (2 * alpha^5 * mu * c) / (3 * pi^2 * sqrt(2) * mu_0 * e^2)
NATIVE_LAMB_PREFACTOR_HZ = (2.0 * ALPHA**5 * MU_H * C) / (3.0 * math.pi**2 * math.sqrt(2.0) * MU_0 * E_CHARGE**2)


def rational_continuity_transition(r: float, r_trans: float = R_TRANS_M) -> float:
    """Return fluid continuity transition factor T(r) = R_trans / (R_trans + r)."""
    return r_trans / (r_trans + r)


def sonic_choking_radius(Z: int = 1) -> float:
    """
    Inner acoustic crossover radius where radial inflow reaches grid wave speed c:
        v(r_sonic) = c * sqrt(2 * Z * r_e / r_sonic) = c  =>  r_sonic(Z) = 2 * Z * r_e
    """
    return 2.0 * Z * R_E


def rational_inner_continuity_transition(r: float, Z: int = 1) -> float:
    """Return inner sonic choking rational continuity factor T_inner(r) = r / (r + r_sonic(Z))."""
    r_sonic = sonic_choking_radius(Z)
    return r / (r + r_sonic)


def effective_operator_bracket(r: float, Z: int = 1, r_trans: float = R_TRANS_M) -> float:
    """
    Return dimensionless bracket U(r) = r^2 * K_grad^2(r) = (2Z / a_mu) * [r * R_trans / (R_trans + r)].
    - For r << R_trans: U(r) ~ (2Z / a_mu) * r  (linear in r, Coulomb gradient).
    - For r >> R_trans: U(r) -> (2Z * R_trans / a_mu) = g_0 = const (Euler-Cauchy scale invariance).
    """
    t_factor = rational_continuity_transition(r, r_trans)
    return (2.0 * Z / A_MU) * r * t_factor


def asymptotic_euler_cauchy_g0(Z: int = 1, r_trans: float = R_TRANS_M) -> float:
    """Return asymptotic scale-free constant g_0 = 2Z * R_trans / a_mu."""
    return (2.0 * Z * r_trans) / A_MU


def dielectric_strain_volume_factor_static(n: int, Z: int = 1) -> float:
    """
    Static core boundary model (sharp cutoff at r_e):
        S_static(n, Z) = ln(r_n / r_e) = ln(n^2 / (Z * alpha^2))
    Normalized to Hydrogen (n=2, Z=1) baseline:
        eta_static = ln(n^2 / (Z * alpha^2)) / ln(4 / alpha^2)
    """
    s_val = math.log((n ** 2) / (Z * ALPHA ** 2))
    s_ref = math.log(4.0 / (1.0 * ALPHA ** 2))
    return s_val / s_ref


def dielectric_strain_volume_factor_rational(n: int, Z: int = 1) -> float:
    """
    Rational continuity sonic choking strain volume factor (Section VI dual profile):
    Integrating T_inner(r) / r across the acoustic cavity from 0 to r_n(Z):
        S_rational(n, Z) = integral_0^{r_n} dr / (r + 2 * Z * r_e) = ln(1 + r_n / (2 * Z * r_e))
        where r_n(Z) = n^2 * a_mu / Z = n^2 * r_e / (Z * alpha^2)
        => r_n / (2 * Z * r_e) = n^2 / (2 * Z^2 * alpha^2)
        S_rational(n, Z) = ln(1 + n^2 / (2 * Z^2 * alpha^2))
    Normalized to Hydrogen (n=2, Z=1) baseline:
        eta_rational = S_rational(n, Z) / S_rational(2, 1)
    """
    s_val = math.log(1.0 + (n ** 2) / (2.0 * (Z ** 2) * (ALPHA ** 2)))
    s_ref = math.log(1.0 + 4.0 / (2.0 * (1.0 ** 2) * (ALPHA ** 2)))
    return s_val / s_ref


def dielectric_strain_volume_factor(n: int, Z: int = 1, mode: str = "rational") -> float:
    """Dielectric strain volume factor. Defaults to the rational continuity sonic profile."""
    if mode == "static":
        return dielectric_strain_volume_factor_static(n, Z)
    return dielectric_strain_volume_factor_rational(n, Z)


def lamb_shift_frequency_native_hz(n: int, Z: int = 1, with_strain: bool = True, mode: str = "rational") -> float:
    """Calculate Lamb shift beat frequency in pure native grid parameters (NO h, NO hbar)."""
    raw_hz = NATIVE_LAMB_PREFACTOR_HZ * (Z ** 4) / (n ** 3)
    if not with_strain:
        return raw_hz
    return raw_hz * dielectric_strain_volume_factor(n, Z, mode=mode)


def run_benchmark() -> list[dict]:
    rows = []

    # 1. Micro Asymptotic Limit (Atomic Scale r = 1 Bohr radius)
    r_atom = A_MU
    u_atom = effective_operator_bracket(r_atom, Z=1)
    linear_coulomb_expected = (2.0 * 1.0 / A_MU) * r_atom  # = 2.0 exactly
    t_atom = rational_continuity_transition(r_atom)
    rows.append({
        "scale_regime": "MICRO (Atomic Core Flow, r << R_trans)",
        "radius_m": f"{r_atom:.4e}",
        "T_transition_factor": f"{t_atom:.8f}",
        "bracket_U_val": f"{u_atom:.8f}",
        "asymptotic_target": f"Coulomb Gradient = {linear_coulomb_expected:.1f}",
        "residual_pct": f"{(u_atom / linear_coulomb_expected - 1.0) * 100.0:+.6f} %",
        "physical_regime": "Steep Central Gradient (r^2 K^2 ~ r => r_n = n^2 a_0)",
    })

    # 2. Intermediate Boundary Layer (r = R_trans = 1 mm)
    r_mid = R_TRANS_M
    u_mid = effective_operator_bracket(r_mid, Z=1)
    t_mid = rational_continuity_transition(r_mid)
    rows.append({
        "scale_regime": "INTERMEDIATE (Acoustic Boundary Layer, r = R_trans)",
        "radius_m": f"{r_mid:.4e}",
        "T_transition_factor": f"{t_mid:.8f}",
        "bracket_U_val": f"{u_mid:.4e}",
        "asymptotic_target": "50% Core Gradient / 50% Bulk Flow",
        "residual_pct": f"{(t_mid - 0.5) * 100.0:+.2f} %",
        "physical_regime": "Continuity Crossover (v_inflow ~ v_bulk)",
    })

    # 3. Macro Asymptotic Limit (Solar System 1 AU)
    r_macro = 1.495978707e11
    u_macro = effective_operator_bracket(r_macro, Z=1)
    g0_macro = asymptotic_euler_cauchy_g0(Z=1)
    t_macro = rational_continuity_transition(r_macro)
    rows.append({
        "scale_regime": "MACRO (Circumstellar Bulk Flow, r >> R_trans)",
        "radius_m": f"{r_macro:.4e}",
        "T_transition_factor": f"{t_macro:.4e}",
        "bracket_U_val": f"{u_macro:.4e}",
        "asymptotic_target": f"Euler-Cauchy Constant g_0 = {g0_macro:.4e}",
        "residual_pct": f"{(u_macro / g0_macro - 1.0) * 100.0:+.6f} %",
        "physical_regime": "Scale-Free Constant Wave Speed (r^2 K^2 -> g_0 => r_n = r_0 k^n)",
    })

    # 4. Helium+ / Hydrogen Lamb Ratio Comparison (Dielectric Strain Saturation)
    nu_H_stat = lamb_shift_frequency_native_hz(2, Z=1, with_strain=True, mode="static")
    nu_He_raw = lamb_shift_frequency_native_hz(2, Z=2, with_strain=False)
    nu_He_stat = lamb_shift_frequency_native_hz(2, Z=2, with_strain=True, mode="static")

    nu_H_rat = lamb_shift_frequency_native_hz(2, Z=1, with_strain=True, mode="rational")
    nu_He_rat = lamb_shift_frequency_native_hz(2, Z=2, with_strain=True, mode="rational")
    obs_ratio = 14041.45 / 1057.85  # Empirical NIST ratio ~ 13.2736
    
    rows.append({
        "scale_regime": "GRID STRAIN SATURATION (Raw Geometric Z^4)",
        "radius_m": "n=2, Z=2 vs Z=1",
        "T_transition_factor": "—",
        "bracket_U_val": f"Ratio = {nu_He_raw / nu_H_stat:.2f}",
        "asymptotic_target": f"NIST Observed Ratio = {obs_ratio:.2f}",
        "residual_pct": f"{( (nu_He_raw / nu_H_stat) / obs_ratio - 1.0) * 100.0:+.2f} %",
        "physical_regime": "Raw Geometric Z^4 Volume Scaling (+20.5% overshoot)",
    })

    rows.append({
        "scale_regime": "GRID STRAIN SATURATION (Static Core ln(r_n/r_e))",
        "radius_m": "n=2, Z=2 vs Z=1",
        "T_transition_factor": f"eta_strain = {dielectric_strain_volume_factor(2, Z=2, mode='static'):.4f}",
        "bracket_U_val": f"Ratio = {nu_He_stat / nu_H_stat:.2f}",
        "asymptotic_target": f"NIST Observed Ratio = {obs_ratio:.2f}",
        "residual_pct": f"{( (nu_He_stat / nu_H_stat) / obs_ratio - 1.0) * 100.0:+.2f} %",
        "physical_regime": "Static Boundary S = ln(n^2/Z*alpha^2) (+13.1% residual, boundary placed)",
    })

    rows.append({
        "scale_regime": "GRID STRAIN SATURATION (Rational Continuity Sonic Choking)",
        "radius_m": "n=2, Z=2 vs Z=1",
        "T_transition_factor": f"eta_strain = {dielectric_strain_volume_factor(2, Z=2, mode='rational'):.4f}",
        "bracket_U_val": f"Ratio = {nu_He_rat / nu_H_rat:.2f}",
        "asymptotic_target": f"NIST Observed Ratio = {obs_ratio:.2f}",
        "residual_pct": f"{( (nu_He_rat / nu_H_rat) / obs_ratio - 1.0) * 100.0:+.2f} %",
        "physical_regime": "Rational Sonic Horizon S = ln(1 + n^2/2Z^2*alpha^2) (+4.68% residual)",
    })

    RESULTS.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS / "constitutive_profile_benchmark.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return rows


def print_summary(rows: list[dict]) -> None:
    print("Hydrodynamic Constitutive Profile & Grid Saturation Benchmark (Paper 4, TICKET-04):")
    for r in rows:
        print(f"  {r['scale_regime']:<48} | Bracket={r['bracket_U_val']:<16} | Res: {r['residual_pct']:<10} | {r['physical_regime']}")


if __name__ == "__main__":
    rows = run_benchmark()
    print_summary(rows)

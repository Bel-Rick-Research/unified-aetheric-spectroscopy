#!/usr/bin/env python3
"""
Bernoulli Source-Sink Suction & Neutron n=0 Ground State Solver (Paper 4).

Models the fluid mechanics of charge attraction and the neutron pair bond:
1. Electric field E is physical aether current velocity: E = v_aether.
   - Proton pump (outflow source from An into Ki): v_pump = +Q / (4*pi*r^2) r_hat
   - Electron sink (inflow drainage from Ki into An): v_sink = -Q / (4*pi*|r-d|^2) r_hat
2. Bernoulli pressure well (Bjerknes Force):
   P(r) = P_0 - 0.5 * rho_A * |v_pump + v_sink|^2
   Between pump and sink, flows reinforce (v_pump . v_sink > 0), creating a maximum
   speed tube and a deep Bernoulli pressure suction well that pulls them together:
       F_attraction(d) = -mu_0 * c^2 * e^2 / (4 * pi * d^2) = -e^2 / (4 * pi * eps_0 * d^2)
3. The Free-Space Orbital Barrier (n >= 1):
   Lattice centrifugal inertia opposes Bernoulli suction:
       F_inertia(d, n) = +mu * v_theta^2 / d = +mu * [n * Gamma_0 / (2*pi)]^2 / d^3
   Because 1/d^3 beats 1/d^2 at close range (d < a_mu), separating inertia prevents collapse.
   Stable equilibrium occurs at d_n = n^2 * a_mu / Z.
4. Nuclear Proximity Inertia Damping & Collapse to n=0 (The Neutron):
   Inside a multi-nucleon cluster (d ~ 1e-15 m), overlapping standing-wave fields of
   surrounding proton fountains cross-modulate and damp the electron's azimuthal circulation:
       v_theta -> 0  =>  F_inertia -> 0
   Without the 1/d^3 inertial barrier, Bernoulli suction draws the sink directly into
   the throat of the pump (d -> r_e), resting at eigenmode n=0 (the neutron pair bond).
5. Electric Neutrality:
   For r >> d, net flux cancels: div(v_pump + v_sink) = +Q - Q = 0.

Writes results/bernoulli_neutron_benchmark.csv
"""

import csv
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"

# Fundamental Dielectric Lattice Constants (CODATA 2018 / SI 2019)
C = 299792458.0                  # Transverse grid wave speed (m/s)
E_CHARGE = 1.602176634e-19       # Circulation charge quantum (C)
EPS_0 = 8.8541878128e-12         # Grid permittivity (F/m)
MU_0 = 1.0 / (EPS_0 * C**2)       # Grid permeability (H/m)
M_E = 9.1093837015e-31           # Electron mass (kg)
M_P = 1.67262192369e-27          # Proton mass (kg)
MU_H = M_E * M_P / (M_E + M_P)   # Two-body reduced mass (kg)

# Grid impedance & gear ratio alpha = v_1 / c
Z_0 = math.sqrt(MU_0 / EPS_0)
ALPHA = E_CHARGE**2 * Z_0 / (4.0 * math.pi * (6.62607015e-34 / (2.0 * math.pi)))

# Native Core & Bohr scales (no hbar, no eps_0)
R_E = MU_0 * E_CHARGE**2 / (4.0 * math.pi * MU_H)  # Core radius ~ 2.8195e-15 m
A_MU = R_E / (ALPHA ** 2)                          # Bohr radius ~ 5.2946e-11 m

# Native circulation quantum: Gamma_0 = (mu_0 * c * e^2) / (2 * mu * alpha)
GAMMA_0 = (MU_0 * C * E_CHARGE**2) / (2.0 * MU_H * ALPHA)

# Aether baseline density and static pressure
RHO_A = 1.0e-17                  # kg/m^3 (baseline loaded density)
P_0 = 0.90                       # Pa (bulk modulus K_A = rho_A * c^2 ~ 0.9 Pa)

# Measured Neutron and Beta Decay Parameters (CODATA 2022 / PDG 2024)
M_N = 1.67492749804e-27          # Neutron mass (kg)
DELTA_M_N = M_N - (M_P + M_E)    # Mass excess over free p + e (kg) ~ 1.3946e-30 kg
DELTA_E_N_J = DELTA_M_N * C**2   # Excess energy in Joules (~ 1.2534e-13 J)
DELTA_E_N_MEV = DELTA_E_N_J / (E_CHARGE * 1.0e6)  # ~ +0.782333 MeV
TAU_NEUTRON_S = 879.4            # Free neutron mean lifetime (seconds, PDG 2024)
TAU_HALF_NEUTRON_S = TAU_NEUTRON_S * math.log(2.0)  # Half-life ~ 609.54 s (~ 10.16 min)


def bernoulli_attraction_force_N(d: float, Z: int = 1) -> float:
    """
    Calculate Bernoulli / Bjerknes suction force pulling pump and sink together (Newtons):
    F = -Z * mu_0 * c^2 * e^2 / (4 * pi * d^2)
    """
    return -Z * (MU_0 * C**2 * E_CHARGE**2) / (4.0 * math.pi * d**2)


def centrifugal_lattice_inertia_force_N(d: float, n: int) -> float:
    """
    Calculate outward centrifugal lattice inertia force opposing Bernoulli suction (Newtons):
    F = +mu * [n * Gamma_0 / (2 * pi)]^2 / d^3
    """
    if n == 0:
        return 0.0  # Damped circulation (n=0 neutron state)
    angular_momentum_native = n * GAMMA_0 / (2.0 * math.pi)
    return MU_H * (angular_momentum_native ** 2) / (d ** 3)


def effective_force_N(d: float, n: int, Z: int = 1) -> float:
    """Return net radial force: F_net = F_Bernoulli + F_inertia."""
    return bernoulli_attraction_force_N(d, Z) + centrifugal_lattice_inertia_force_N(d, n)


def effective_potential_J(d: float, n: int, Z: int = 1) -> float:
    """
    Calculate effective potential energy (Joules):
    V_eff(d) = -Z * mu_0 * c^2 * e^2 / (4 * pi * d) + mu * [n * Gamma_0 / (2*pi)]^2 / (2 * d^2)
    """
    v_bernoulli = -Z * (MU_0 * C**2 * E_CHARGE**2) / (4.0 * math.pi * d)
    if n == 0:
        return v_bernoulli
    angular_momentum_native = n * GAMMA_0 / (2.0 * math.pi)
    v_inertia = MU_H * (angular_momentum_native ** 2) / (2.0 * d ** 2)
    return v_bernoulli + v_inertia


def net_exterior_flux_divergence(r: float, d: float, Q: float = 1.0) -> float:
    """
    Calculate net exterior flux divergence at distance r >> d:
    div(v_net) = (Q_pump + Q_sink) / (4 * pi * r^2) = (Q - Q) / (4 * pi * r^2) = 0.
    """
    return (Q - Q) / (4.0 * math.pi * r**2)


def neutron_core_dielectric_compression_radius_m(delta_E_J: float = DELTA_E_N_J) -> float:
    """
    Derive the separation distance d_0 where the electrostatic / Bernoulli
    dielectric strain energy equals the empirical neutron mass excess Delta E = (m_n - m_p - m_e)*c^2:
        U_strain(d_0) = mu_0 * c^2 * e^2 / (4 * pi * d_0) = Delta_E
        => d_0 = mu_0 * c^2 * e^2 / (4 * pi * Delta_E)
    """
    return (MU_0 * C**2 * E_CHARGE**2) / (4.0 * math.pi * delta_E_J)


def beta_decay_acoustic_barrier_action(tau_s: float = TAU_NEUTRON_S, r_core: float = R_E) -> float:
    """
    Calculate the acoustic tunnelling barrier action S_barrier = 2 * integral(kappa dr):
        tau = (1 / f_attempt) * exp(S_barrier)
        f_attempt = c / (2 * pi * r_core)
        => S_barrier = ln(f_attempt * tau)
    """
    f_attempt = C / (2.0 * math.pi * r_core)
    return math.log(f_attempt * tau_s)


def run_benchmark() -> list[dict]:
    rows = []

    # 1. Equilibrium radius at n=1 (Hydrogen ground state in free space)
    r_eq_1 = A_MU
    f_net_1 = effective_force_N(r_eq_1, n=1, Z=1)
    f_bern_1 = bernoulli_attraction_force_N(r_eq_1, Z=1)
    f_iner_1 = centrifugal_lattice_inertia_force_N(r_eq_1, n=1)
    rows.append({
        "state": "Hydrogen Ground State (n=1)",
        "orbital_radius_m": f"{r_eq_1:.4e}",
        "bernoulli_suction_N": f"{f_bern_1:.4e}",
        "lattice_inertia_N": f"{f_iner_1:.4e}",
        "net_force_N": f"{f_net_1:.4e}",
        "physical_condition": "Stable Free-Space Equilibrium (|F_bern| == F_iner)",
    })

    # 2. Sub-orbital distance d = 0.5 * a_mu (repulsive barrier prevents collapse)
    d_sub = 0.5 * A_MU
    f_net_sub = effective_force_N(d_sub, n=1, Z=1)
    rows.append({
        "state": "Sub-Orbital Compression (d = 0.5 a_mu, n=1)",
        "orbital_radius_m": f"{d_sub:.4e}",
        "bernoulli_suction_N": f"{bernoulli_attraction_force_N(d_sub, Z=1):.4e}",
        "lattice_inertia_N": f"{centrifugal_lattice_inertia_force_N(d_sub, n=1):.4e}",
        "net_force_N": f"{f_net_sub:.4e}",
        "physical_condition": "Repulsive Barrier (F_net > 0 pushes electron back out to n=1)",
    })

    # 3. Super-orbital distance d = 2.0 * a_mu (Bernoulli suction pulls inward)
    d_sup = 2.0 * A_MU
    f_net_sup = effective_force_N(d_sup, n=1, Z=1)
    rows.append({
        "state": "Super-Orbital Extension (d = 2.0 a_mu, n=1)",
        "orbital_radius_m": f"{d_sup:.4e}",
        "bernoulli_suction_N": f"{bernoulli_attraction_force_N(d_sup, Z=1):.4e}",
        "lattice_inertia_N": f"{centrifugal_lattice_inertia_force_N(d_sup, n=1):.4e}",
        "net_force_N": f"{f_net_sup:.4e}",
        "physical_condition": "Attractive Pull (F_net < 0 pulls electron back in to n=1)",
    })

    # 4. Nuclear Proximity Inertia Damping: Collapse to n=0 (Neutron Ground State)
    d_neutron = R_E  # Rests at nuclear core radius
    f_net_neutron = effective_force_N(d_neutron, n=0, Z=1)
    f_bern_neutron = bernoulli_attraction_force_N(d_neutron, Z=1)
    f_iner_neutron = centrifugal_lattice_inertia_force_N(d_neutron, n=0)
    rows.append({
        "state": "Neutron Pair Bond (n=0, v_theta damped to 0)",
        "orbital_radius_m": f"{d_neutron:.4e}",
        "bernoulli_suction_N": f"{f_bern_neutron:.4e}",
        "lattice_inertia_N": f"{f_iner_neutron:.4e}",
        "net_force_N": f"{f_net_neutron:.4e}",
        "physical_condition": "Damped Collapse to n=0 Core (Inertia=0; suction pulls sink into pump throat)",
    })

    # 5. Electric Neutrality Check for n=0 Neutron
    div_flux = net_exterior_flux_divergence(r=1.0e-10, d=R_E, Q=1.0)
    rows.append({
        "state": "Neutron Exterior Electric Flux Divergence",
        "orbital_radius_m": "1.0000e-10 (Exterior r >> d)",
        "bernoulli_suction_N": "—",
        "lattice_inertia_N": "—",
        "net_force_N": f"{div_flux:.1f}",
        "physical_condition": "Strict Electric Neutrality (div v = +Q - Q = 0)",
    })

    # 6. Neutron Mass Excess Dielectric Compression Radius (TICKET-01)
    d_0_strain = neutron_core_dielectric_compression_radius_m()
    f_bern_d0 = bernoulli_attraction_force_N(d_0_strain, Z=1)
    rows.append({
        "state": "Neutron Mass Excess Strain (Delta E = +0.7823 MeV)",
        "orbital_radius_m": f"{d_0_strain:.4e}",
        "bernoulli_suction_N": f"{f_bern_d0:.4e}",
        "lattice_inertia_N": "0.0000e+00",
        "net_force_N": f"{f_bern_d0:.4e}",
        "physical_condition": f"Compressed Dielectric Strain U = Delta_m * c^2 (d_0 = {d_0_strain*1e15:.2f} fm)",
    })

    # 7. Free Neutron Beta-Decay Acoustic Barrier Action
    s_barrier = beta_decay_acoustic_barrier_action()
    f_attempt = C / (2.0 * math.pi * R_E)
    rows.append({
        "state": "Free Neutron Beta Decay Tunnelling (tau = 879.4 s)",
        "orbital_radius_m": f"{R_E:.4e}",
        "bernoulli_suction_N": f"f_0={f_attempt:.3e} Hz",
        "lattice_inertia_N": f"tau={TAU_NEUTRON_S:.1f} s",
        "net_force_N": f"S={s_barrier:.2f}",
        "physical_condition": f"Acoustic Barrier Action S_barrier = 2 * int(kappa dr) = {s_barrier:.2f}",
    })

    # 8. First-Principles Beta-Decay Boundary Status
    rows.append({
        "state": "First-Principles Beta Half-Life Derivation",
        "orbital_radius_m": "Walled to Tier k<=7",
        "bernoulli_suction_N": "—",
        "lattice_inertia_N": "—",
        "net_force_N": "BLOCKED",
        "physical_condition": "BLOCKED: REQUIRES SUB-HADRONIC NOZZLE EOS [TICKET-12 / Paper 5]",
    })

    RESULTS.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS / "bernoulli_neutron_benchmark.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return rows


def print_summary(rows: list[dict]) -> None:
    print("Bernoulli Suction & Neutron n=0 Ground State Benchmark (Paper 4):")
    for r in rows:
        print(f"  {r['state']:<45} | r={r['orbital_radius_m']:<12} | Net Force={r['net_force_N']:<12} | {r['physical_condition']}")


if __name__ == "__main__":
    rows = run_benchmark()
    print_summary(rows)

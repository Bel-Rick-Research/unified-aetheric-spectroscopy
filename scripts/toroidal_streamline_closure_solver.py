#!/usr/bin/env python3
"""
Toroidal Recirculating Streamline Contours & Vortex Closure Solver (Paper 4 / TICKET-02).

Models the fluid mechanics of charge topology and toroidal self-confinement:
1. Electric charge as flow direction:
   - An Outflow Pump (+Q, Source from counterspace into 3D space)
   - Ki Sink Drainage (-Q, Drain from 3D space into counterspace)
2. Stokes Streamfunction in Cylindrical Coordinates (varpi, z):
   For axisymmetric incompressible flow, velocity components are:
       v_varpi = -(1 / varpi) * (d psi / d z)
       v_z     = +(1 / varpi) * (d psi / d varpi)
3. Dipolar Pump-Sink Flow Field:
   A source at (0, +d/2) and sink at (0, -d/2) produce Stokes streamfunction:
       psi_dipole(varpi, z) = (Q / (4*pi)) * [ (z - d/2)/sqrt(varpi^2 + (z-d/2)^2) - (z + d/2)/sqrt(varpi^2 + (z+d/2)^2) ]
   Flow lines psi = const connect pump directly to sink along low-pressure Bernoulli tube.
4. Toroidal Recirculating Ring Closure:
   To prevent unconfined axial flux leakage, poloidal flux curls down the pressure gradient
   into a closed toroidal vortex ring of major radius R_0 = a_mu and minor core radius r_0 = r_e = alpha^2 * a_mu:
   Trapped fluid volume inside the separatrix streamline (psi <= psi_sep) moves with the ring,
   forming a self-confined Kelvin-Helmholtz vortex plasmoid.
5. Bernoulli Pressure Distribution:
   P(varpi, z) = P_0 - 0.5 * rho_A * (v_varpi^2 + v_z^2 + v_phi^2)
   Demonstrates minimum pressure at the vortex core and high static confining pressure outside.

Writes results/toroidal_streamline_closure_benchmark.csv
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

# Native core & Bohr radii
R_E = MU_0 * E_CHARGE**2 / (4.0 * math.pi * MU_H)   # ~ 2.8179e-15 m
A_MU = R_E / (ALPHA ** 2)                           # ~ 5.2946e-11 m

# Native circulation quantum: Gamma_0 = (mu_0 * c * e^2) / (2 * mu * alpha)
GAMMA_0 = (MU_0 * C * E_CHARGE**2) / (2.0 * MU_H * ALPHA)

# Aether density and static confining pressure
RHO_A = 1.0e-17                  # kg/m^3 (baseline loaded density)
P_0 = 0.90                       # Pa (bulk modulus K_A)

# Circulation volumetric flux parameter Q = sqrt(mu_0 * c^2 * e^2 / rho_A)
Q_FLUX = math.sqrt(MU_0 * C**2 * E_CHARGE**2 / RHO_A)


def dipole_stokes_streamfunction(varpi: float, z: float, d: float = A_MU, Q: float = Q_FLUX) -> float:
    """
    Compute Stokes streamfunction for coaxial source (+Q at z = +d/2) and sink (-Q at z = -d/2).
    psi(varpi, z) = (Q / 4pi) * [ (z - d/2)/R_1 - (z + d/2)/R_2 ]
    where R_1 = sqrt(varpi^2 + (z - d/2)^2), R_2 = sqrt(varpi^2 + (z + d/2)^2).
    """
    z1 = z - 0.5 * d
    z2 = z + 0.5 * d
    r1 = math.sqrt(varpi**2 + z1**2 + R_E**2)
    r2 = math.sqrt(varpi**2 + z2**2 + R_E**2)
    return (Q / (4.0 * math.pi)) * (z1 / r1 - z2 / r2)


def dipole_velocity_field(varpi: float, z: float, d: float = A_MU, Q: float = Q_FLUX) -> tuple[float, float]:
    """
    Calculate numerical velocity components from Stokes streamfunction:
    v_varpi = -(1 / varpi) * d(psi)/dz
    v_z     = +(1 / varpi) * d(psi)/d(varpi)
    """
    eps = 1.0e-14
    varpi_safe = max(varpi, R_E)

    dpsi_dz = (dipole_stokes_streamfunction(varpi_safe, z + eps, d, Q) -
               dipole_stokes_streamfunction(varpi_safe, z - eps, d, Q)) / (2.0 * eps)
    dpsi_dvarpi = (dipole_stokes_streamfunction(varpi_safe + eps, z, d, Q) -
                   dipole_stokes_streamfunction(varpi_safe - eps, z, d, Q)) / (2.0 * eps)

    v_varpi = -dpsi_dz / varpi_safe
    v_z = dpsi_dvarpi / varpi_safe
    return v_varpi, v_z


def vortex_ring_streamfunction(varpi: float, z: float, R_0: float = A_MU, r_0: float = R_E, gamma: float = GAMMA_0) -> float:
    """
    Regularized circular vortex ring streamfunction (Lamb dipole / Norbury ring approximation).
    s = sqrt((varpi - R_0)^2 + z^2) is distance from the toroidal core centerline.
    For s < r_0: solid body rotation core.
    For s >= r_0: potential irrotational flow outside core.
    """
    s = math.sqrt((varpi - R_0)**2 + z**2)
    if s < r_0:
        # Internal core streamline: quadratic growth with distance s
        return 0.5 * (gamma / (2.0 * math.pi)) * (s / r_0)**2 * varpi
    else:
        # External potential streamline: logarithmic decay with core distance
        return 0.5 * (gamma / (2.0 * math.pi)) * (1.0 + 2.0 * math.log(s / r_0)) * (r_0 / s) * varpi


def vortex_ring_bernoulli_pressure_Pa(varpi: float, z: float, R_0: float = A_MU, r_0: float = R_E) -> float:
    """
    Calculate static fluid pressure via Bernoulli equation:
    P = P_0 - 0.5 * rho_A * (v_poloidal^2 + v_toroidal^2)
    """
    s = max(math.sqrt((varpi - R_0)**2 + z**2), r_0)
    # Circulation speed at distance s from ring filament: v = Gamma_0 / (2 * pi * s)
    v_circ = GAMMA_0 / (2.0 * math.pi * s)
    dyn_p = 0.5 * RHO_A * v_circ**2
    return max(0.0, P_0 - dyn_p)


def vortex_ring_self_induced_velocity_m_s(R_0: float = A_MU, r_0: float = R_E, gamma: float = GAMMA_0) -> float:
    """
    Classical Helmholtz-Lamb formula for self-induced axial propagation speed of a thin vortex ring:
    U = (Gamma / (4 * pi * R_0)) * [ ln(8 * R_0 / r_0) - 1/4 ]
    """
    return (gamma / (4.0 * math.pi * R_0)) * (math.log(8.0 * R_0 / r_0) - 0.25)


def run_benchmark() -> list[dict]:
    rows = []

    # 1. Pump and Sink Coaxial Midpoint (Maximum Bernoulli Suction Tube)
    d = A_MU
    v_varpi_mid, v_z_mid = dipole_velocity_field(varpi=R_E, z=0.0, d=d)
    v_mid_mag = math.sqrt(v_varpi_mid**2 + v_z_mid**2)
    p_mid = max(0.0, P_0 - 0.5 * RHO_A * v_mid_mag**2)
    rows.append({
        "configuration": "Dipolar Coaxial Midpoint (z=0, varpi=r_e)",
        "coordinates_m": f"z=0.0, varpi={R_E:.2e}",
        "velocity_m_s": f"{v_mid_mag:.4e}",
        "streamfunction_m3_s": f"{dipole_stokes_streamfunction(R_E, 0.0, d):.4e}",
        "bernoulli_pressure_Pa": f"{p_mid:.4e}",
        "physical_condition": "Deep Bernoulli suction tube connecting pump and sink",
    })

    # 2. Pump Outflow Nozzle (Near Source at z = +d/2)
    v_varpi_pump, v_z_pump = dipole_velocity_field(varpi=R_E, z=0.5*d - R_E)
    v_pump_mag = math.sqrt(v_varpi_pump**2 + v_z_pump**2)
    rows.append({
        "configuration": "Pump Outflow Throat (z = +d/2 - r_e)",
        "coordinates_m": f"z={(0.5*d - R_E):.2e}, varpi={R_E:.2e}",
        "velocity_m_s": f"{v_pump_mag:.4e}",
        "streamfunction_m3_s": f"{dipole_stokes_streamfunction(R_E, 0.5*d - R_E, d):.4e}",
        "bernoulli_pressure_Pa": f"{max(0.0, P_0 - 0.5*RHO_A*v_pump_mag**2):.4e}",
        "physical_condition": "High-velocity unipolar An outflow fountain (+Q)",
    })

    # 3. Sink Inflow Throat (Near Drain at z = -d/2)
    v_varpi_sink, v_z_sink = dipole_velocity_field(varpi=R_E, z=-0.5*d + R_E)
    v_sink_mag = math.sqrt(v_varpi_sink**2 + v_z_sink**2)
    rows.append({
        "configuration": "Sink Inflow Throat (z = -d/2 + r_e)",
        "coordinates_m": f"z={(-0.5*d + R_E):.2e}, varpi={R_E:.2e}",
        "velocity_m_s": f"{v_sink_mag:.4e}",
        "streamfunction_m3_s": f"{dipole_stokes_streamfunction(R_E, -0.5*d + R_E, d):.4e}",
        "bernoulli_pressure_Pa": f"{max(0.0, P_0 - 0.5*RHO_A*v_sink_mag**2):.4e}",
        "physical_condition": "High-velocity unipolar Ki sink drainage (-Q)",
    })

    # 4. Exterior Flank (High Static Confining Pressure)
    v_varpi_ext, v_z_ext = dipole_velocity_field(varpi=3.0*d, z=0.0, d=d)
    v_ext_mag = math.sqrt(v_varpi_ext**2 + v_z_ext**2)
    p_ext = P_0 - 0.5 * RHO_A * v_ext_mag**2
    rows.append({
        "configuration": "Exterior Transverse Flank (varpi = 3*a_mu, z=0)",
        "coordinates_m": f"z=0.0, varpi={3.0*d:.2e}",
        "velocity_m_s": f"{v_ext_mag:.4e}",
        "streamfunction_m3_s": f"{dipole_stokes_streamfunction(3.0*d, 0.0, d):.4e}",
        "bernoulli_pressure_Pa": f"{p_ext:.4e}",
        "physical_condition": "Near-static background pressure P_0 confines flow tube",
    })

    # 5. Toroidal Vortex Core Centerline (varpi = a_mu, z = 0)
    p_ring_core = vortex_ring_bernoulli_pressure_Pa(A_MU, 0.0, A_MU, R_E)
    psi_ring_core = vortex_ring_streamfunction(A_MU, 0.0, A_MU, R_E)
    rows.append({
        "configuration": "Toroidal Ring Core Centerline (varpi = a_mu, z=0)",
        "coordinates_m": f"z=0.0, varpi={A_MU:.2e}",
        "velocity_m_s": f"{(GAMMA_0 / (2.0*math.pi*R_E)):.4e}",
        "streamfunction_m3_s": f"{psi_ring_core:.4e}",
        "bernoulli_pressure_Pa": f"{p_ring_core:.4e}",
        "physical_condition": "Deepest toroidal pressure suction well; self-confining Kelvin core",
    })

    # 6. Toroidal Ring Aspect Ratio and Hierarchy
    aspect_ratio = A_MU / R_E
    rows.append({
        "configuration": "Toroidal Geometry Aspect Ratio (R_0 / r_0 = 1 / alpha^2)",
        "coordinates_m": f"R_0={A_MU:.2e}, r_0={R_E:.2e}",
        "velocity_m_s": f"alpha={ALPHA:.6f}",
        "streamfunction_m3_s": f"ratio={aspect_ratio:.2f}",
        "bernoulli_pressure_Pa": "—",
        "physical_condition": f"Exact geometric ratio R_0 / r_0 = 1/alpha^2 = {1.0/ALPHA**2:.2f}",
    })

    # 7. Self-Induced Axial Propagation Velocity (Helmholtz-Lamb Ring)
    u_ring = vortex_ring_self_induced_velocity_m_s(A_MU, R_E, GAMMA_0)
    rows.append({
        "configuration": "Vortex Ring Self-Induced Axial Speed (Helmholtz-Lamb)",
        "coordinates_m": f"R_0={A_MU:.2e}, r_0={R_E:.2e}",
        "velocity_m_s": f"{u_ring:.4e}",
        "streamfunction_m3_s": "—",
        "bernoulli_pressure_Pa": "—",
        "physical_condition": f"Thin-core ring speed U = (Gamma/4piR)*[ln(8R/r0) - 1/4] = {u_ring:.2f} m/s",
    })

    RESULTS.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS / "toroidal_streamline_closure_benchmark.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return rows


def print_summary(rows: list[dict]) -> None:
    print("Toroidal Recirculating Streamline Contours & Vortex Closure Benchmark (Paper 4 / TICKET-02):")
    for r in rows:
        print(f"  {r['configuration']:<52} | coords={r['coordinates_m']:<24} | P={r['bernoulli_pressure_Pa']:<10} | {r['physical_condition']}")


if __name__ == "__main__":
    benchmark_rows = run_benchmark()
    print_summary(benchmark_rows)

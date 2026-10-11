"""Teaching models only; SI formulas with explicit eV conversion. Standard library."""
from __future__ import annotations

import json
import math
from pathlib import Path

H = 6.62607015e-34  # J s, exact
HBAR = H / (2 * math.pi)
EV = 1.602176634e-19  # J / eV, exact
KB = 1.380649e-23  # J / K, exact
M0 = 9.1093837139e-31  # kg, CODATA 2022; uncertainty immaterial here
ALPHA = HBAR * HBAR / (2 * M0) / EV * 1e18  # eV nm^2


def band_pair(kappa_nm: float, a_nm: float = 0.5,
              vg_ev: float = 0.05) -> tuple[float, float]:
    if a_nm <= 0 or not all(map(math.isfinite, (kappa_nm, a_nm, vg_ev))):
        raise ValueError("Finite parameters and positive lattice spacing required")
    reciprocal = 2 * math.pi / a_nm
    mean = ALPHA * (reciprocal**2 / 4 + kappa_nm**2)
    split = math.hypot(ALPHA * reciprocal * kappa_nm, vg_ev)
    return mean - split, mean + split


def states_below(dim: int, eps_j: float, mass_kg: float, degeneracy: int) -> float:
    """Allowed states per m^dim below E_c + eps_j, one parabolic valley family."""
    if dim not in (1, 2, 3) or mass_kg <= 0 or not isinstance(degeneracy, int) or degeneracy <= 0:
        raise ValueError("dim=1,2,3; positive mass and degeneracy required")
    if not all(map(math.isfinite, (eps_j, mass_kg, degeneracy))):
        raise ValueError("Finite parameters required")
    if eps_j <= 0:
        return 0.0
    k = math.sqrt(2 * mass_kg * eps_j) / HBAR
    volumes = {1: 2 * k, 2: math.pi * k*k, 3: 4 * math.pi * k**3 / 3}
    return degeneracy * volumes[dim] / (2 * math.pi)**dim


def dos_j(dim: int, eps_j: float, mass_kg: float, degeneracy: int) -> float:
    """DOS in m^(-dim) J^-1; 1D edge diverges integrably."""
    # Validate even below edge rather than allowing malformed material parameters.
    states_below(dim, eps_j, mass_kg, degeneracy)
    if eps_j < 0:
        return 0.0
    if eps_j == 0:
        if dim == 1:
            return math.inf
        if dim == 3:
            return 0.0
        return degeneracy * mass_kg / (2 * math.pi * HBAR**2)
    return dim * states_below(dim, eps_j, mass_kg, degeneracy) / (2 * eps_j)


def finite_box_count(dim: int, eps_j: float, mass_kg: float,
                     degeneracy: int, length_m: float) -> int:
    """Direct integer k-grid enumeration, with floor(radius) <= 100."""
    states_below(dim, eps_j, mass_kg, degeneracy)
    if length_m <= 0 or not math.isfinite(length_m):
        raise ValueError("Positive finite length required")
    if eps_j < 0:
        return 0
    radius = math.sqrt(2 * mass_kg * eps_j) / HBAR * length_m / (2 * math.pi)
    bound = math.floor(radius)
    if bound > 100:
        raise ValueError("Teaching enumeration requires floor(radius) <=100")
    axis = range(-bound, bound + 1)
    r2 = radius * radius
    if dim == 1:
        points = sum(i*i <= r2 for i in axis)
    elif dim == 2:
        points = sum(i*i+j*j <= r2 for i in axis for j in axis)
    else:
        points = sum(i*i+j*j+k*k <= r2 for i in axis for j in axis for k in axis)
    return int(degeneracy * points)


def midpoint_integral(func, lo: float, hi: float, panels: int) -> float:
    if panels <= 0:
        raise ValueError("Positive panel count required")
    step = (hi-lo) / panels
    return math.fsum(func(lo+(i+0.5)*step) for i in range(panels)) * step


def nc_3d(mass_kg: float, degeneracy: int, temp_k: float) -> float:
    if temp_k <= 0 or not math.isfinite(temp_k):
        raise ValueError("Positive finite temperature required")
    states_below(3, EV, mass_kg, degeneracy)
    return degeneracy * (mass_kg * KB * temp_k / (2*math.pi*HBAR**2))**1.5


def density_3d(ef_minus_ec_ev: float, mass_kg: float = 0.2*M0,
               degeneracy: int = 2, temp_k: float = 300,
               panels: int = 20000, cutoff_ev: float = 1.0,
               mode: str = "fd") -> float:
    """Numerical integral after eps_eV=t^2 substitution; finite upper cutoff."""
    if (temp_k <= 0 or cutoff_ev <= 0 or mode not in ("fd", "mb")
            or not all(map(math.isfinite, (ef_minus_ec_ev, temp_k, cutoff_ev)))):
        raise ValueError("Positive T and cutoff; mode fd/mb required")
    thermal_ev = KB * temp_k / EV
    def integrand(t):
        eps_ev = t*t
        x = (eps_ev-ef_minus_ec_ev) / thermal_ev
        exp_negative = math.exp(-x) if x >= 0 else None
        f = (exp_negative/(1+exp_negative) if x >= 0
             else 1/(1+math.exp(x))) if mode == "fd" else math.exp(-x)
        return dos_j(3, eps_ev*EV, mass_kg, degeneracy) * EV * f * 2*t
    return midpoint_integral(integrand, 0, math.sqrt(cutoff_ev), panels)


def svg_plot(path: Path, title: str, xlabel: str, ylabel: str,
             xrange: tuple[float, float], yrange: tuple[float, float],
             curves: list[tuple[str, str, list[tuple[float, float]], bool]]) -> None:
    """Small deterministic SVG; plotted values carry units in axis labels."""
    import html
    esc = html.escape
    width, height = 900, 520
    left, right, top, bottom = 110, 850, 70, 420
    def px(x): return left+(x-xrange[0])/(xrange[1]-xrange[0])*(right-left)
    def py(y): return bottom-(y-yrange[0])/(yrange[1]-yrange[0])*(bottom-top)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="900" height="520" fill="white"/>',
           '<g font-family="sans-serif" fill="#17202a" font-size="16">',
           f'<text x="450" y="30" text-anchor="middle" font-size="21">{esc(title)}</text>']
    for i in range(6):
        xv=xrange[0]+i*(xrange[1]-xrange[0])/5
        yv=yrange[0]+i*(yrange[1]-yrange[0])/5
        out.append(f'<path d="M {px(xv):.2f} {top} V {bottom} M {left} {py(yv):.2f} H {right}" stroke="#e7ebef" fill="none"/>')
        out.append(f'<text x="{px(xv):.2f}" y="{bottom+25}" text-anchor="middle">{xv:.3g}</text>')
        out.append(f'<text x="{left-12}" y="{py(yv)+5:.2f}" text-anchor="end">{yv:.3g}</text>')
    out.append(f'<path d="M {left} {top} V {bottom} H {right}" stroke="#17202a" fill="none"/>')
    for idx,(label,color,points,dashed) in enumerate(curves):
        pts=" ".join(f"{px(x):.3f},{py(y):.3f}" for x,y in points)
        dash=' stroke-dasharray="7 5"' if dashed else ''
        out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.8"{dash}/>')
        out.append(f'<text x="{left+idx*230}" y="485" fill="{color}">{esc(label)}</text>')
    out.extend([f'<text x="480" y="465" text-anchor="middle">{esc(xlabel)}</text>',
                f'<text transform="translate(27 245) rotate(-90)" text-anchor="middle">{esc(ylabel)}</text>', '</g></svg>'])
    path.write_text("\n".join(out)+"\n", encoding="utf-8")


def run(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    edge = ALPHA*(math.pi/0.5)**2
    bands = band_pair(0)
    detuned = band_pair(0.02)
    counts = []
    for dim in (1, 2, 3):
        exact = finite_box_count(dim, .05*EV, .2*M0, 2, 200e-9)
        continuous = states_below(dim, .05*EV, .2*M0, 2)*(200e-9)**dim
        counts.append({"dim": dim, "finite_states": exact, "continuum_states": continuous,
                       "relative_count_error": abs(exact-continuous)/continuous})
    nc=nc_3d(.2*M0, 2, 300)
    analytic=nc*math.exp(-.1*EV/(KB*300))
    fd=density_3d(-.1)
    mb=density_3d(-.1, mode="mb")
    results={"model": "1D two-wave weak periodic potential and separate 3D isotropic band",
             "units": {"band_energy": "eV", "density": "m^-3", "kappa": "nm^-1"},
             "alpha_eV_nm2":ALPHA, "E0_eV":edge,"edge_eigenvalues_eV":bands,
             "gap_eV":bands[1]-bands[0], "kappa_0p02_eigenvalues_eV":detuned,
             "finite_box":counts, "Nc_m3":nc, "n_MB_analytic_m3":analytic,
             "n_MB_numerical_m3":mb, "n_FD_numerical_m3":fd,
             "MB_relative_error_using_FD":(analytic-fd)/fd,
             "FD_panel_refinement_relative_change":abs(fd-density_3d(-.1, panels=10000))/fd,
             "FD_cutoff_refinement_relative_change":abs(fd-density_3d(-.1,cutoff_ev=2))/fd,
             "integration": {"method":"midpoint after epsilon_eV=t^2 substitution", "panels":20000, "cutoff_eV":1.0}}
    (output_dir/"results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    xs=[-.15+.3*i/400 for i in range(401)]
    recip=2*math.pi/.5
    path=output_dir/"bragg-gap.svg"
    svg_plot(path,"Two-wave avoided crossing: a=0.50 nm, |VG|=0.050 eV",
             "kappa = k - G/2 [nm^-1]", "E - E0 [eV]",(-.15,.15),(-.10,.10),[
             ("coupled lower","#1565c0",[(x,band_pair(x)[0]-edge) for x in xs],False),
             ("coupled upper","#d35400",[(x,band_pair(x)[1]-edge) for x in xs],False),
             ("free (+)","#6c757d",[(x,ALPHA*x*x+ALPHA*recip*x) for x in xs],True),
             ("free (-)","#7f8c8d",[(x,ALPHA*x*x-ALPHA*recip*x) for x in xs],True)])
    eps=[.005+.195*i/400 for i in range(401)]
    svg_plot(output_dir/"dos-dimensions.svg","DOS shape: separate line / area / volume densities",
             "epsilon = E - Ec [eV]", "g(E) / g(Ec + 0.05 eV) [1]",(0,.2),(0,3.5),[
             (f"{d}D (normalized)",color,[(e,dos_j(d,e*EV,.2*M0,2)/dos_j(d,.05*EV,.2*M0,2)) for e in eps],False)
             for d,color in ((1,"#1565c0"),(2,"#d35400"),(3,"#117864"))])
    eps=[.4*i/400 for i in range(401)]
    def spectrum(e, mode):
        x=(e+.1)/(KB*300/EV)
        f=1/(1+math.exp(x)) if mode=="fd" else math.exp(-x)
        return dos_j(3,e*EV,.2*M0,2)*EV*f/1e24
    svg_plot(output_dir/"occupied-spectrum.svg","Occupied spectrum: m*=0.20 m0, g=2, T=300 K, EF-Ec=-0.10 eV",
             "epsilon = E - Ec [eV]", "g(E) f(E) [10^24 m^-3 eV^-1]",(0,.4),(0,1.0),[
             ("Fermi-Dirac","#1565c0",[(e,spectrum(e,"fd")) for e in eps],False),
             ("Maxwell-Boltzmann","#d35400",[(e,spectrum(e,"mb")) for e in eps],True)])
    return results


if __name__ == "__main__":
    # Write only under this practice directory, single-threaded, no external packages.
    print(json.dumps(run(Path(__file__).resolve().parent/"assets"),ensure_ascii=False,indent=2))

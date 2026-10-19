"""Command-line entry point: ``opentcad info | demo-diode | models | gui``."""

from __future__ import annotations

import argparse
import csv
import json
import sys


def _cmd_info(_: argparse.Namespace) -> int:
    from opentcad import __version__
    from opentcad._devsim import solver_info
    from opentcad.materials import MaterialDB

    info = solver_info()
    db = MaterialDB.load()
    print(f"opentcad {__version__}")
    print(
        f"devsim {info.get('version')}  solver={info.get('direct_solver_active')}  "
        f"(OPENTCAD_SOLVER={info.get('opentcad_solver_choice')}, "
        f"OPENTCAD_PRECISION={info.get('opentcad_precision')})"
    )
    if info.get("mkl_version"):
        print(f"MKL: {info['mkl_version']}")
    print(f"materials: {', '.join(db.materials())}  parameter status: {db.status_counts()}")
    return 0


def _cmd_models(_: argparse.Namespace) -> int:
    from opentcad.literature import load_references
    from opentcad.physics import available

    refs = load_references()
    for m in available():
        cites = "; ".join(refs[s].short() if s in refs else f"MISSING:{s}" for s in m.sources)
        print(f"{m.id:28s} {m.spec:12s} {m.status:12s} {m.name}\n    sources: {cites}")
    return 0


def _cmd_demo_diode(args: argparse.Namespace) -> int:
    from opentcad._devsim import reset
    from opentcad.devices import DiodeParams, build_pn_diode_1d
    from opentcad.solver import enable_drift_diffusion, solve_dc, solve_equilibrium, sweep_bias

    reset()
    # Demo inputs: eps_r is an explicit input because silicon's permittivity is still
    # "needs-source" in the material DB (backlog P1-MAT-001).
    params = DiodeParams(relative_permittivity=args.eps_r, intrinsic_density_cm3=args.ni)
    dev = build_pn_diode_1d(params)
    solve_equilibrium()
    enable_drift_diffusion(dev)
    solve_dc()
    points = sweep_bias(dev, dev.anode, stop_V=args.vmax, step_V=args.step)
    rows = [{"V_anode": p.bias_V, "J_anode_A_cm2": p.currents_A_per_cm2[dev.anode]} for p in points]
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {len(rows)} points to {args.csv}")
    else:
        print(json.dumps(rows, indent=2))
    return 0


def _cmd_gui(_: argparse.Namespace) -> int:
    from opentcad.gui.app import run

    return run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opentcad", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info", help="versions, linear solver and material-DB status")
    sub.add_parser("models", help="list registered physics models with their sources")
    demo = sub.add_parser("demo-diode", help="forward I-V sweep of the 1D reference diode")
    demo.add_argument("--vmax", type=float, default=0.5)
    demo.add_argument("--step", type=float, default=0.05)
    demo.add_argument(
        "--eps-r", type=float, default=11.7, help="explicit relative permittivity input"
    )
    demo.add_argument(
        "--ni", type=float, default=1.0e10, help="explicit intrinsic density input (cm^-3)"
    )
    demo.add_argument("--csv", help="write results to this CSV file")
    sub.add_parser("gui", help="start the desktop application (needs the [gui] extra)")
    args = parser.parse_args(argv)
    handlers = {
        "info": _cmd_info,
        "models": _cmd_models,
        "demo-diode": _cmd_demo_diode,
        "gui": _cmd_gui,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

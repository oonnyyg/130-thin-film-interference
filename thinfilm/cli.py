"""Command-line interface.

Usage:
  python -m thinfilm run --config stack.json --wavelengths waves.csv \
      --out-dir out
  python -m thinfilm optimize --config stack.json --layer 0 \
      --wavelength 550 --candidates 80,90,100,110
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .core import compute_spectrum
from .materials import MaterialError
from .optimize import OptimizeError, optimize_layer_thickness
from .report import summarize, write_spectrum_csv, write_summary
from .wavelengths import WavelengthError, load_wavelengths


def _cmd_run(args: argparse.Namespace) -> int:
    stack = load_config(args.config)
    wavelengths = load_wavelengths(args.wavelengths)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    forward = compute_spectrum(stack, wavelengths)
    backward = compute_spectrum(stack.reversed(), wavelengths)
    fwd_csv = "forward.csv"
    bwd_csv = "backward.csv"
    write_spectrum_csv(forward, out_dir / fwd_csv)
    write_spectrum_csv(backward, out_dir / bwd_csv)
    summary = {
        "config": str(args.config),
        "wavelengths": str(args.wavelengths),
        "forward": summarize("forward", forward, fwd_csv),
        "backward": summarize("backward", backward, bwd_csv),
    }
    write_summary(summary, out_dir / "summary.json")
    print(f"wrote {out_dir / fwd_csv}, {out_dir / bwd_csv}, {out_dir / 'summary.json'}")
    return 0


def _cmd_optimize(args: argparse.Namespace) -> int:
    stack = load_config(args.config)
    candidates = [float(x) for x in args.candidates.split(",") if x.strip()]
    result = optimize_layer_thickness(stack, args.layer, args.wavelength, candidates)
    print(
        json.dumps(
            {
                "layer_index": result.layer_index,
                "wavelength_nm": result.wavelength_nm,
                "best_thickness_nm": result.best_thickness_nm,
                "reflectance": result.reflectance,
                "transmittance": result.transmittance,
                "candidates_evaluated": result.candidates_evaluated,
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="thinfilm",
        description="Normal-incidence lossless thin-film R/T calculator",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="compute forward/backward spectra")
    run.add_argument("--config", required=True, help="JSON stack config")
    run.add_argument("--wavelengths", required=True, help="CSV of wavelengths (nm)")
    run.add_argument("--out-dir", required=True, help="output directory")
    run.set_defaults(func=_cmd_run)
    opt = sub.add_parser("optimize", help="single-layer thickness search")
    opt.add_argument("--config", required=True, help="JSON stack config")
    opt.add_argument("--layer", type=int, default=0, help="layer index (default 0)")
    opt.add_argument("--wavelength", type=float, required=True, help="target nm")
    opt.add_argument(
        "--candidates", required=True, help="comma-separated thicknesses (nm)"
    )
    opt.set_defaults(func=_cmd_optimize)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, WavelengthError, MaterialError, OptimizeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

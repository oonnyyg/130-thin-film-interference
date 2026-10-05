"""Command line interface: python -m thinfilm config.json [-o outdir]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .materials import ConfigError
from .report import build_summary, evaluate, write_csv, write_summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="thinfilm",
        description=(
            "Normal-incidence lossless multilayer reflectance/transmittance "
            "via the coherent characteristic-matrix method."
        ),
    )
    parser.add_argument("config", help="path to the JSON configuration file")
    parser.add_argument(
        "-o",
        "--outdir",
        default=".",
        help="output directory for forward.csv, reverse.csv, summary.json",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        results = evaluate(config)
    except (ConfigError, OSError, ArithmeticError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    write_csv(outdir / "forward.csv", results["forward"])
    write_csv(outdir / "reverse.csv", results["reverse"])
    summary = build_summary(config, results)
    write_summary(outdir / "summary.json", summary)

    fwd = summary["forward"]["reflectance_extrema"]
    print(
        "wrote forward.csv, reverse.csv, summary.json to "
        f"{outdir.resolve()}"
    )
    print(
        f"forward R: min {fwd['min']['reflectance']:.6g} @ "
        f"{fwd['min']['wavelength_nm']:g} nm, max {fwd['max']['reflectance']:.6g} @ "
        f"{fwd['max']['wavelength_nm']:g} nm"
    )
    if "optimization" in summary:
        opt = summary["optimization"]
        print(
            f"optimization: layer {opt['layer_index']} best thickness "
            f"{opt['best_thickness_nm']:g} nm (R={opt['best_reflectance']:.6g} "
            f"@ {opt['wavelength_nm']:g} nm)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

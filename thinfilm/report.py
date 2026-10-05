"""Spectra evaluation, extrema, optimization and export helpers."""

from __future__ import annotations

import csv
import json

from .config import Config
from .solver import Layer, Stack, solve_point, solve_stack

ENERGY_TOLERANCE = 1e-9


def extrema(points):
    """Reflectance min/max; ties resolve to the shorter wavelength."""
    best_min = min(points, key=lambda p: (p.reflectance, p.wavelength_nm))
    best_max = max(points, key=lambda p: (p.reflectance, -p.wavelength_nm))
    return best_min, best_max


def check_energy(points, tolerance=ENERGY_TOLERANCE):
    worst = max(abs(p.energy_residual) for p in points)
    if worst > tolerance:
        raise ArithmeticError(
            f"energy conservation violated: max |R+T-1| = {worst:.3e} "
            f"(tolerance {tolerance:.1e})"
        )
    return worst


def optimize_layer(config: Config):
    """Try each candidate thickness for one layer; lowest forward R wins,
    ties resolve to the thinner candidate. The original config is untouched."""
    spec = config.optimize
    stack = config.stack
    results = []
    for candidate in spec.candidates_nm:
        layers = list(stack.layers)
        old = layers[spec.layer_index]
        layers[spec.layer_index] = Layer(
            material=old.material, thickness_nm=candidate
        )
        trial = Stack(
            incident=stack.incident, substrate=stack.substrate, layers=tuple(layers)
        )
        point = solve_point(trial, spec.wavelength_nm)
        results.append((candidate, point.reflectance))
    best_thickness, best_r = min(results, key=lambda item: (item[1], item[0]))
    return {
        "layer_index": spec.layer_index,
        "wavelength_nm": spec.wavelength_nm,
        "best_thickness_nm": best_thickness,
        "best_reflectance": best_r,
        "candidates": [
            {"thickness_nm": t, "reflectance": r} for t, r in results
        ],
    }


def evaluate(config: Config):
    forward = solve_stack(config.stack, config.wavelengths_nm)
    reverse = solve_stack(config.stack.reversed(), config.wavelengths_nm)
    fwd_residual = check_energy(forward)
    rev_residual = check_energy(reverse)
    return {
        "forward": forward,
        "reverse": reverse,
        "forward_residual": fwd_residual,
        "reverse_residual": rev_residual,
    }


def write_csv(path, points):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["wavelength_nm", "reflectance", "transmittance", "energy_residual"]
        )
        for p in points:
            writer.writerow(
                [
                    f"{p.wavelength_nm:.6g}",
                    f"{p.reflectance:.12g}",
                    f"{p.transmittance:.12g}",
                    f"{p.energy_residual:.3e}",
                ]
            )


def _extrema_json(points):
    lo, hi = extrema(points)
    return {
        "min": {"wavelength_nm": lo.wavelength_nm, "reflectance": lo.reflectance},
        "max": {"wavelength_nm": hi.wavelength_nm, "reflectance": hi.reflectance},
    }


def build_summary(config: Config, results):
    summary = {
        "wavelengths_nm": list(config.wavelengths_nm),
        "forward": {
            "incident": config.stack.incident.name,
            "substrate": config.stack.substrate.name,
            "max_abs_energy_residual": results["forward_residual"],
            "reflectance_extrema": _extrema_json(results["forward"]),
        },
        "reverse": {
            "incident": config.stack.substrate.name,
            "substrate": config.stack.incident.name,
            "max_abs_energy_residual": results["reverse_residual"],
            "reflectance_extrema": _extrema_json(results["reverse"]),
        },
    }
    if config.optimize is not None:
        summary["optimization"] = optimize_layer(config)
    return summary


def write_summary(path, summary):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

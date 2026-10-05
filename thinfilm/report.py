"""Spectrum export (CSV) and JSON summary helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .core import SpectrumPoint

ENERGY_TOLERANCE = 1e-9


def write_spectrum_csv(points: list[SpectrumPoint], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
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
                    f"{p.energy_residual:.6g}",
                ]
            )


def _extremum(points: list[SpectrumPoint], key, pick_min: bool) -> dict:
    best = points[0]
    for p in points[1:]:
        better = key(p) < key(best) if pick_min else key(p) > key(best)
        tie_shorter = key(p) == key(best) and p.wavelength_nm < best.wavelength_nm
        if better or tie_shorter:
            best = p
    return {"wavelength_nm": best.wavelength_nm, "value": key(best)}


def summarize(direction: str, points: list[SpectrumPoint], csv_name: str) -> dict:
    max_residual = max(abs(p.energy_residual) for p in points)
    return {
        "direction": direction,
        "csv": csv_name,
        "points": len(points),
        "max_abs_energy_residual": max_residual,
        "energy_check_passed": max_residual <= ENERGY_TOLERANCE,
        "reflectance_min": _extremum(points, lambda p: p.reflectance, True),
        "reflectance_max": _extremum(points, lambda p: p.reflectance, False),
    }


def write_summary(summary: dict, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

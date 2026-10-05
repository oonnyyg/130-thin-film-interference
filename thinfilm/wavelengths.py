"""Parsing of the wavelength CSV input (one wavelength in nm per row)."""

from __future__ import annotations

import csv
import math
from pathlib import Path


class WavelengthError(ValueError):
    """Raised for invalid wavelength CSV input."""


def load_wavelengths(source: str | Path) -> list[float]:
    """Read wavelengths (nm) from a CSV file.

    Accepts a single numeric column; an optional header row named
    'wavelength'/'wavelength_nm' (case-insensitive) is skipped. Any invalid
    or duplicate value rejects the whole file (no partial spectra).
    """
    text = Path(source).read_text(encoding="utf-8-sig")
    values: list[float] = []
    for lineno, row in enumerate(csv.reader(text.splitlines()), start=1):
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) != 1:
            raise WavelengthError(f"line {lineno}: expected a single column")
        cell = row[0].strip()
        if lineno == 1 and cell.lower() in ("wavelength", "wavelength_nm", "nm"):
            continue
        try:
            wl = float(cell)
        except ValueError:
            raise WavelengthError(
                f"line {lineno}: invalid wavelength value {cell!r}"
            ) from None
        if not math.isfinite(wl) or wl <= 0.0:
            raise WavelengthError(
                f"line {lineno}: wavelength must be a positive finite number"
            )
        values.append(wl)
    if not values:
        raise WavelengthError("no wavelengths found in file")
    return values

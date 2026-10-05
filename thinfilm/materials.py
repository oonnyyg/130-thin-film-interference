"""Material refractive-index models: constant or tabulated vs wavelength."""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass


class MaterialError(ValueError):
    """Raised for invalid material definitions or out-of-range lookups."""


def _check_index(value: float, context: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise MaterialError(f"{context}: refractive index must be a number")
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise MaterialError(
            f"{context}: refractive index must be a positive finite number"
        )
    return value


@dataclass(frozen=True)
class Material:
    """A lossless material with a real refractive index.

    Either a positive constant, or a table of (wavelength_nm, index) pairs
    with strictly increasing positive wavelengths. Table lookups use linear
    interpolation; extrapolation outside the table range is forbidden.
    """

    name: str
    constant: float | None = None
    table: tuple[tuple[float, float], ...] | None = None

    @classmethod
    def from_constant(cls, name: str, n: float) -> "Material":
        return cls(name=name, constant=_check_index(n, name))

    @classmethod
    def from_table(cls, name: str, pairs: list[tuple[float, float]]) -> "Material":
        if len(pairs) < 2:
            raise MaterialError(f"{name}: table needs at least two points")
        cleaned: list[tuple[float, float]] = []
        prev_wl = None
        for wl, n in pairs:
            if not isinstance(wl, (int, float)) or isinstance(wl, bool):
                raise MaterialError(f"{name}: table wavelength must be a number")
            wl = float(wl)
            if not math.isfinite(wl) or wl <= 0.0:
                raise MaterialError(f"{name}: table wavelengths must be positive")
            if prev_wl is not None and wl <= prev_wl:
                raise MaterialError(
                    f"{name}: table wavelengths must be strictly increasing"
                )
            cleaned.append((wl, _check_index(n, f"{name} @ {wl} nm")))
            prev_wl = wl
        return cls(name=name, table=tuple(cleaned))

    def index_at(self, wavelength_nm: float) -> float:
        """Refractive index at the given wavelength (nm)."""
        if self.constant is not None:
            return self.constant
        assert self.table is not None
        wls = [p[0] for p in self.table]
        if wavelength_nm < wls[0] or wavelength_nm > wls[-1]:
            raise MaterialError(
                f"{self.name}: wavelength {wavelength_nm} nm is outside the "
                f"table range [{wls[0]}, {wls[-1]}] nm; extrapolation is not allowed"
            )
        i = bisect_left(wls, wavelength_nm)
        if wls[i] == wavelength_nm:
            return self.table[i][1]
        (w0, n0), (w1, n1) = self.table[i - 1], self.table[i]
        t = (wavelength_nm - w0) / (w1 - w0)
        return n0 + t * (n1 - n0)

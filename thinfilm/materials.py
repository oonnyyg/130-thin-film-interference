"""Material definitions: constant or tabulated real refractive index."""

from __future__ import annotations

import math
from dataclasses import dataclass


class ConfigError(ValueError):
    """Raised when the user-supplied configuration is invalid."""


def _check_positive_finite(value, what):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigError(f"{what} must be a number, got {value!r}")
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ConfigError(f"{what} must be a positive finite number, got {value!r}")
    return value


@dataclass(frozen=True)
class Material:
    """Lossless material: constant index or a wavelength table."""

    name: str
    constant: float | None = None
    table: tuple[tuple[float, ...], tuple[float, ...]] | None = None

    @classmethod
    def from_json(cls, name, spec):
        if isinstance(spec, (int, float)) and not isinstance(spec, bool):
            return cls(name=name, constant=_check_positive_finite(spec, f"n of {name}"))
        if isinstance(spec, dict) and "wavelengths_nm" in spec and "n" in spec:
            waves = spec["wavelengths_nm"]
            indices = spec["n"]
            if (
                not isinstance(waves, list)
                or not isinstance(indices, list)
                or len(waves) != len(indices)
                or len(waves) < 2
            ):
                raise ConfigError(
                    f"table of {name}: wavelengths_nm and n must be lists "
                    "of equal length >= 2"
                )
            waves = tuple(
                _check_positive_finite(w, f"wavelength of {name}") for w in waves
            )
            indices = tuple(
                _check_positive_finite(v, f"n of {name}") for v in indices
            )
            for prev, cur in zip(waves, waves[1:]):
                if cur <= prev:
                    raise ConfigError(
                        f"table of {name}: wavelengths must be strictly increasing"
                    )
            return cls(name=name, table=(waves, indices))
        raise ConfigError(
            f"material {name}: n must be a positive number or a table with "
            "'wavelengths_nm' and 'n'"
        )

    @property
    def is_constant(self):
        return self.constant is not None

    def index_at(self, wavelength_nm):
        """Index at ``wavelength_nm``; linear interpolation, no extrapolation."""
        if self.constant is not None:
            return self.constant
        waves, indices = self.table
        if wavelength_nm < waves[0] or wavelength_nm > waves[-1]:
            raise ConfigError(
                f"wavelength {wavelength_nm} nm outside table range "
                f"[{waves[0]}, {waves[-1]}] nm of material {self.name!r}; "
                "extrapolation is not allowed"
            )
        lo, hi = 0, len(waves) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if waves[mid] <= wavelength_nm:
                lo = mid
            else:
                hi = mid
        w0, w1 = waves[lo], waves[hi]
        n0, n1 = indices[lo], indices[hi]
        frac = (wavelength_nm - w0) / (w1 - w0)
        return n0 + frac * (n1 - n0)

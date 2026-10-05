"""Normal-incidence thin-film interference calculator (stdlib only).

Conventions
-----------
- Wavelengths and thicknesses are in nanometres (nm).
- Phase convention: the propagation phase of a layer of thickness d and
  refractive index n at vacuum wavelength lambda0 is
      delta = 2 * pi * n * d / lambda0
  using the exp(-i*omega*t) time convention, so the characteristic matrix
  of a layer is
      M = [[cos(delta), i*sin(delta)/n],
           [i*n*sin(delta), cos(delta)]]
- All refractive indices are real and positive (lossless, non-absorbing).
"""

from .materials import Material
from .core import Stack, SpectrumPoint, compute_spectrum
from .config import load_config, ConfigError

__all__ = [
    "Material",
    "Stack",
    "SpectrumPoint",
    "compute_spectrum",
    "load_config",
    "ConfigError",
]

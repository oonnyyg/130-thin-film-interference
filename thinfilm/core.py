"""Coherent characteristic-matrix (transfer matrix) computation.

Normal incidence, lossless layers. The stack characteristic matrix is the
ordered product of per-layer matrices, so all propagation phases and
multiple reflections are preserved (interface Fresnel coefficients are
never summed directly).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .materials import Material

TAU = 2.0 * math.pi


@dataclass(frozen=True)
class Layer:
    material: Material
    thickness_nm: float

    def __post_init__(self) -> None:
        d = self.thickness_nm
        if not isinstance(d, (int, float)) or isinstance(d, bool):
            raise ValueError("layer thickness must be a number")
        if not math.isfinite(d) or d < 0.0:
            raise ValueError("layer thickness must be a non-negative finite number")


@dataclass(frozen=True)
class Stack:
    """Incident medium, ordered layers (incident side first), substrate."""

    incident: Material
    layers: tuple[Layer, ...]
    substrate: Material

    def reversed(self) -> "Stack":
        """Stack for illumination from the substrate side."""
        return Stack(
            incident=self.substrate,
            layers=tuple(reversed(self.layers)),
            substrate=self.incident,
        )


@dataclass(frozen=True)
class SpectrumPoint:
    wavelength_nm: float
    reflectance: float
    transmittance: float
    energy_residual: float  # R + T - 1, should be ~0 for lossless stacks


def _layer_matrix(n: float, thickness_nm: float, wavelength_nm: float):
    delta = TAU * n * thickness_nm / wavelength_nm
    c = math.cos(delta)
    s = math.sin(delta)
    return ((c, 1j * s / n), (1j * n * s, c))


def _matmul(a, b):
    return (
        (a[0][0] * b[0][0] + a[0][1] * b[1][0], a[0][0] * b[0][1] + a[0][1] * b[1][1]),
        (a[1][0] * b[0][0] + a[1][1] * b[1][0], a[1][0] * b[0][1] + a[1][1] * b[1][1]),
    )


def compute_point(stack: Stack, wavelength_nm: float) -> SpectrumPoint:
    """Reflectance/transmittance of the stack at one wavelength (nm)."""
    if not math.isfinite(wavelength_nm) or wavelength_nm <= 0.0:
        raise ValueError("wavelength must be a positive finite number")
    m = ((1.0 + 0.0j, 0.0 + 0.0j), (0.0 + 0.0j, 1.0 + 0.0j))
    for layer in stack.layers:
        n = layer.material.index_at(wavelength_nm)
        m = _matmul(m, _layer_matrix(n, layer.thickness_nm, wavelength_nm))
    n0 = stack.incident.index_at(wavelength_nm)
    ns = stack.substrate.index_at(wavelength_nm)
    (m11, m12), (m21, m22) = m
    denom = n0 * m11 + n0 * ns * m12 + m21 + ns * m22
    r = (n0 * m11 + n0 * ns * m12 - m21 - ns * m22) / denom
    t = 2.0 * n0 / denom
    reflectance = abs(r) ** 2
    # Power transmittance: scale |t|^2 by the admittance (here index) ratio
    # of substrate to incident medium.
    transmittance = (ns / n0) * abs(t) ** 2
    residual = reflectance + transmittance - 1.0
    return SpectrumPoint(wavelength_nm, reflectance, transmittance, residual)


def compute_spectrum(stack: Stack, wavelengths_nm: list[float]) -> list[SpectrumPoint]:
    """Spectrum over the given wavelengths; rejects duplicates/invalid values."""
    seen: set[float] = set()
    for wl in wavelengths_nm:
        if not isinstance(wl, (int, float)) or isinstance(wl, bool):
            raise ValueError(f"invalid wavelength value: {wl!r}")
        if not math.isfinite(wl) or wl <= 0.0:
            raise ValueError(f"wavelength must be a positive finite number: {wl!r}")
        if wl in seen:
            raise ValueError(f"duplicate wavelength: {wl} nm")
        seen.add(wl)
    return [compute_point(stack, wl) for wl in wavelengths_nm]

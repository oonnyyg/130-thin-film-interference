"""Coherent characteristic-matrix solver for lossless multilayers.

Phase convention: a layer of index n and physical thickness d (nm) at
vacuum wavelength lam (nm) carries phase delta = 2*pi*n*d/lam. The
characteristic matrix of one layer at normal incidence is

    M = [[cos(delta), i*sin(delta)/n],
         [i*n*sin(delta), cos(delta)]]

and the stack matrix is the ordered product M1*M2*...*Mk from the
incident side to the substrate. With incident index n0 and substrate
index ns the field amplitudes are

    r = (n0*A + n0*ns*B - C - ns*D) / (n0*A + n0*ns*B + C + ns*D)
    t = 2*n0 / (n0*A + n0*ns*B + C + ns*D)

with M = [[A, B], [C, D]]. Power coefficients are R = |r|^2 and
T = (ns/n0)*|t|^2 (real indices, normal incidence).
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass

from .materials import Material


@dataclass(frozen=True)
class Layer:
    material: Material
    thickness_nm: float


@dataclass(frozen=True)
class Stack:
    incident: Material
    substrate: Material
    layers: tuple[Layer, ...]

    def reversed(self) -> "Stack":
        """Stack illuminated from the substrate side."""
        return Stack(
            incident=self.substrate,
            substrate=self.incident,
            layers=tuple(reversed(self.layers)),
        )


@dataclass(frozen=True)
class SpectrumPoint:
    wavelength_nm: float
    reflectance: float
    transmittance: float
    energy_residual: float  # R + T - 1


def _layer_matrix(n: complex, thickness_nm: float, wavelength_nm: float):
    delta = 2.0 * math.pi * n * thickness_nm / wavelength_nm
    cos_d = cmath.cos(delta)
    sin_d = cmath.sin(delta)
    return ((cos_d, 1j * sin_d / n), (1j * n * sin_d, cos_d))


def _matmul(m1, m2):
    (a1, b1), (c1, d1) = m1
    (a2, b2), (c2, d2) = m2
    return (
        (a1 * a2 + b1 * c2, a1 * b2 + b1 * d2),
        (c1 * a2 + d1 * c2, c1 * b2 + d1 * d2),
    )


def solve_point(stack: Stack, wavelength_nm: float) -> SpectrumPoint:
    n0 = stack.incident.index_at(wavelength_nm)
    ns = stack.substrate.index_at(wavelength_nm)
    total = ((1.0 + 0.0j, 0.0 + 0.0j), (0.0 + 0.0j, 1.0 + 0.0j))
    for layer in stack.layers:
        if layer.thickness_nm == 0.0:
            continue  # zero-thickness layers carry no phase
        n = layer.material.index_at(wavelength_nm)
        total = _matmul(total, _layer_matrix(n, layer.thickness_nm, wavelength_nm))
    (a, b), (c, d) = total
    denom = n0 * a + n0 * ns * b + c + ns * d
    r = (n0 * a + n0 * ns * b - c - ns * d) / denom
    t = (2.0 * n0) / denom
    refl = abs(r) ** 2
    trans = (ns / n0) * abs(t) ** 2
    return SpectrumPoint(
        wavelength_nm=wavelength_nm,
        reflectance=refl,
        transmittance=trans,
        energy_residual=refl + trans - 1.0,
    )


def solve_stack(stack: Stack, wavelengths_nm) -> list[SpectrumPoint]:
    return [solve_point(stack, w) for w in wavelengths_nm]

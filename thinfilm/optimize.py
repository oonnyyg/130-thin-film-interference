"""Single-layer thickness search over candidate values."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .core import Layer, Stack, compute_point


class OptimizeError(ValueError):
    """Raised for invalid optimization requests."""


@dataclass(frozen=True)
class OptimizeResult:
    layer_index: int
    wavelength_nm: float
    best_thickness_nm: float
    reflectance: float
    transmittance: float
    candidates_evaluated: int


def optimize_layer_thickness(
    stack: Stack,
    layer_index: int,
    wavelength_nm: float,
    candidates_nm: list[float],
) -> OptimizeResult:
    """Find the candidate thickness minimising forward reflectance.

    Ties in reflectance (within 1e-12) are broken towards the thinner
    candidate. The input stack is not modified.
    """
    if not 0 <= layer_index < len(stack.layers):
        raise OptimizeError(f"layer index {layer_index} out of range")
    if not candidates_nm:
        raise OptimizeError("candidate list must not be empty")
    candidates: list[float] = []
    for d in candidates_nm:
        if not isinstance(d, (int, float)) or isinstance(d, bool):
            raise OptimizeError(f"invalid candidate thickness: {d!r}")
        if not math.isfinite(d) or d < 0.0:
            raise OptimizeError(f"candidate thickness must be non-negative: {d!r}")
        candidates.append(float(d))
    best_d: float | None = None
    best_r = math.inf
    best_t = 0.0
    for d in candidates:
        layers = list(stack.layers)
        old = layers[layer_index]
        layers[layer_index] = Layer(material=old.material, thickness_nm=d)
        trial = replace(stack, layers=tuple(layers))
        pt = compute_point(trial, wavelength_nm)
        is_better = pt.reflectance < best_r - 1e-12
        is_tie_thinner = (
            abs(pt.reflectance - best_r) <= 1e-12
            and best_d is not None
            and d < best_d
        )
        if is_better or is_tie_thinner:
            best_d, best_r, best_t = d, pt.reflectance, pt.transmittance
    assert best_d is not None
    return OptimizeResult(
        layer_index=layer_index,
        wavelength_nm=wavelength_nm,
        best_thickness_nm=best_d,
        reflectance=best_r,
        transmittance=best_t,
        candidates_evaluated=len(candidates),
    )

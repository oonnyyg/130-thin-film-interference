"""JSON configuration loading and validation."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

from .materials import ConfigError, Material
from .solver import Layer, Stack


@dataclass(frozen=True)
class OptimizeSpec:
    layer_index: int
    wavelength_nm: float
    candidates_nm: tuple[float, ...]


@dataclass(frozen=True)
class Config:
    stack: Stack
    wavelengths_nm: tuple[float, ...]
    optimize: OptimizeSpec | None = None


def _load_material(spec, default_name):
    if isinstance(spec, dict) and "n" in spec and "wavelengths_nm" not in spec:
        name = spec.get("name", default_name)
        return Material.from_json(name, spec["n"])
    if isinstance(spec, dict) and "wavelengths_nm" in spec:
        name = spec.get("name", default_name)
        return Material.from_json(name, spec)
    return Material.from_json(default_name, spec)


def _check_wavelengths(values) -> tuple[float, ...]:
    if not isinstance(values, list) or not values:
        raise ConfigError("wavelengths_nm must be a non-empty list")
    out = []
    seen = set()
    for v in values:
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise ConfigError(f"invalid wavelength {v!r}")
        v = float(v)
        if not math.isfinite(v) or v <= 0.0:
            raise ConfigError(f"wavelength must be positive and finite, got {v!r}")
        if v in seen:
            raise ConfigError(f"duplicate wavelength {v} nm")
        seen.add(v)
        out.append(v)
    return tuple(out)


def _check_thickness(value, what) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigError(f"{what} must be a number, got {value!r}")
    value = float(value)
    if not math.isfinite(value) or value < 0.0:
        raise ConfigError(f"{what} must be non-negative and finite, got {value!r}")
    return value


def parse_config(data) -> Config:
    if not isinstance(data, dict):
        raise ConfigError("top-level configuration must be a JSON object")
    for key in ("incident", "substrate", "wavelengths_nm"):
        if key not in data:
            raise ConfigError(f"missing required key {key!r}")
    incident = _load_material(data["incident"], "incident")
    substrate = _load_material(data["substrate"], "substrate")
    raw_layers = data.get("layers", [])
    if not isinstance(raw_layers, list):
        raise ConfigError("layers must be a list")
    layers = []
    for i, raw in enumerate(raw_layers):
        if not isinstance(raw, dict) or "thickness_nm" not in raw or "n" not in raw:
            raise ConfigError(
                f"layer {i}: needs 'thickness_nm' and 'n' (number or table)"
            )
        name = raw.get("name", f"layer{i}")
        material = Material.from_json(name, raw["n"])
        thickness = _check_thickness(raw["thickness_nm"], f"thickness of layer {i}")
        layers.append(Layer(material=material, thickness_nm=thickness))
    wavelengths = _check_wavelengths(data["wavelengths_nm"])
    optimize = _parse_optimize(data.get("optimize"), len(layers))
    return Config(
        stack=Stack(incident=incident, substrate=substrate, layers=tuple(layers)),
        wavelengths_nm=wavelengths,
        optimize=optimize,
    )


def _parse_optimize(raw, n_layers) -> OptimizeSpec | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ConfigError("optimize must be an object")
    try:
        index = raw["layer_index"]
        wavelength = raw["wavelength_nm"]
        candidates = raw["candidates_nm"]
    except KeyError as exc:
        raise ConfigError(f"optimize: missing key {exc}") from None
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < n_layers:
        raise ConfigError(f"optimize.layer_index must be an integer in [0, {n_layers})")
    wavelength = float(wavelength)
    if not math.isfinite(wavelength) or wavelength <= 0.0:
        raise ConfigError("optimize.wavelength_nm must be positive and finite")
    if not isinstance(candidates, list) or not candidates:
        raise ConfigError("optimize.candidates_nm must be a non-empty list")
    checked = tuple(
        _check_thickness(c, "optimize candidate thickness") for c in candidates
    )
    return OptimizeSpec(
        layer_index=index, wavelength_nm=wavelength, candidates_nm=checked
    )


def load_config(path) -> Config:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return parse_config(data)

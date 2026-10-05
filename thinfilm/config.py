"""JSON configuration loading and validation.

Config schema:
{
  "incident":  {"name": "air", "n": 1.0},
  "substrate": {"name": "glass", "n": 1.52},
  "layers": [
    {"material": {"name": "MgF2", "n": 1.38}, "thickness_nm": 97.6},
    {"material": {"name": "TiO2",
                  "table": [[450.0, 2.45], [550.0, 2.35], [650.0, 2.28]]},
     "thickness_nm": 60.0}
  ]
}

A material has either "n" (positive constant) or "table" (list of
[wavelength_nm, index] pairs, strictly increasing positive wavelengths).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .core import Layer, Stack
from .materials import Material, MaterialError


class ConfigError(ValueError):
    """Raised for invalid configuration files."""


def _parse_material(spec: object, context: str) -> Material:
    if not isinstance(spec, dict):
        raise ConfigError(f"{context}: material must be an object")
    name = spec.get("name", context)
    if not isinstance(name, str) or not name:
        raise ConfigError(f"{context}: material name must be a non-empty string")
    has_n = "n" in spec
    has_table = "table" in spec
    if has_n == has_table:
        raise ConfigError(
            f"{context} ({name}): specify exactly one of 'n' or 'table'"
        )
    try:
        if has_n:
            return Material.from_constant(name, spec["n"])
        table = spec["table"]
        if not isinstance(table, list):
            raise MaterialError(f"{name}: table must be a list of [wavelength, n]")
        pairs = []
        for row in table:
            if not isinstance(row, (list, tuple)) or len(row) != 2:
                raise MaterialError(f"{name}: table rows must be [wavelength, n]")
            pairs.append((row[0], row[1]))
        return Material.from_table(name, pairs)
    except MaterialError as exc:
        raise ConfigError(f"{context}: {exc}") from exc


def load_config(source: str | Path) -> Stack:
    """Load and validate a JSON config file into a Stack."""
    try:
        data = json.loads(Path(source).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("config root must be an object")
    for key in ("incident", "substrate", "layers"):
        if key not in data:
            raise ConfigError(f"missing required key: {key!r}")
    incident = _parse_material(data["incident"], "incident")
    substrate = _parse_material(data["substrate"], "substrate")
    raw_layers = data["layers"]
    if not isinstance(raw_layers, list):
        raise ConfigError("'layers' must be a list")
    layers: list[Layer] = []
    for i, entry in enumerate(raw_layers):
        ctx = f"layers[{i}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{ctx}: layer must be an object")
        if "material" not in entry or "thickness_nm" not in entry:
            raise ConfigError(f"{ctx}: needs 'material' and 'thickness_nm'")
        material = _parse_material(entry["material"], f"{ctx}.material")
        d = entry["thickness_nm"]
        if not isinstance(d, (int, float)) or isinstance(d, bool):
            raise ConfigError(f"{ctx}: thickness_nm must be a number")
        if not math.isfinite(d) or d < 0.0:
            raise ConfigError(f"{ctx}: thickness_nm must be non-negative")
        layers.append(Layer(material=material, thickness_nm=float(d)))
    return Stack(incident=incident, layers=tuple(layers), substrate=substrate)

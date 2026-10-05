"""Normal-incidence thin-film interference calculator (absorption-free)."""

from .solver import Stack, Layer, solve_stack
from .materials import Material

__all__ = ["Stack", "Layer", "solve_stack", "Material"]

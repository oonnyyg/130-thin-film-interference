import math
import unittest

from thinfilm import Material, Stack, compute_spectrum
from thinfilm.core import Layer, compute_point


def const(name, n):
    return Material.from_constant(name, n)


class SingleInterfaceTests(unittest.TestCase):
    def test_bare_interface_matches_fresnel(self):
        stack = Stack(const("air", 1.0), (), const("glass", 1.5))
        p = compute_spectrum(stack, [550.0])[0]
        self.assertAlmostEqual(p.reflectance, 0.04, places=12)
        self.assertAlmostEqual(p.transmittance, 0.96, places=12)
        self.assertAlmostEqual(p.energy_residual, 0.0, places=12)

    def test_zero_thickness_layer_is_invisible(self):
        mgf2 = const("MgF2", 1.38)
        bare = Stack(const("air", 1.0), (), const("glass", 1.5))
        with_zero = Stack(const("air", 1.0), (Layer(mgf2, 0.0),), const("glass", 1.5))
        for wl in (400.0, 550.0, 700.0):
            a = compute_point(bare, wl)
            b = compute_point(with_zero, wl)
            self.assertAlmostEqual(a.reflectance, b.reflectance, places=12)
            self.assertAlmostEqual(a.transmittance, b.transmittance, places=12)


class QuarterWaveTests(unittest.TestCase):
    def test_quarter_wave_ar_coating_minimum(self):
        # MgF2 quarter-wave at 550 nm on glass: near-zero reflectance.
        n_f = 1.38
        d = 550.0 / (4.0 * n_f)
        stack = Stack(
            const("air", 1.0), (Layer(const("MgF2", n_f), d),), const("glass", 1.52)
        )
        p = compute_point(stack, 550.0)
        expected = ((1.52 - n_f**2) / (1.52 + n_f**2)) ** 2
        self.assertAlmostEqual(p.reflectance, expected, places=10)
        self.assertLess(p.reflectance, 0.02)

    def test_quarter_wave_high_index_maximum(self):
        # Quarter-wave of high index on glass increases reflectance.
        n_h = 2.3
        d = 550.0 / (4.0 * n_h)
        stack = Stack(
            const("air", 1.0), (Layer(const("TiO2", n_h), d),), const("glass", 1.52)
        )
        p = compute_point(stack, 550.0)
        expected = ((n_h**2 - 1.52) / (n_h**2 + 1.52)) ** 2
        self.assertAlmostEqual(p.reflectance, expected, places=10)
        self.assertGreater(p.reflectance, 0.15)

    def test_half_wave_layer_is_absentee(self):
        n = 2.0
        d = 550.0 / (2.0 * n)
        bare = Stack(const("air", 1.0), (), const("glass", 1.52))
        coated = Stack(const("air", 1.0), (Layer(const("x", n), d),), const("glass", 1.52))
        self.assertAlmostEqual(
            compute_point(bare, 550.0).reflectance,
            compute_point(coated, 550.0).reflectance,
            places=10,
        )


class AsymmetricStackTests(unittest.TestCase):
    def setUp(self):
        self.air = const("air", 1.0)
        self.glass = const("glass", 1.52)
        self.layers = (
            Layer(const("L", 1.38), 100.0),
            Layer(const("H", 2.3), 55.0),
            Layer(const("M", 1.7), 80.0),
        )

    def test_forward_backward_reflectance_equal_lossless(self):
        # Physical invariant: a lossless reciprocal stack has the same
        # reflectance from both sides (only the phase of r changes).
        stack = Stack(self.air, self.layers, self.glass)
        fwd = compute_point(stack, 550.0)
        bwd = compute_point(stack.reversed(), 550.0)
        self.assertAlmostEqual(fwd.reflectance, bwd.reflectance, places=10)

    def test_layer_order_matters(self):
        # Same layers in a different order give a different spectrum,
        # proving propagation phases and multiple reflections are kept.
        forward_order = Stack(self.air, self.layers, self.glass)
        shuffled = Stack(
            self.air,
            (self.layers[1], self.layers[0], self.layers[2]),
            self.glass,
        )
        a = compute_point(forward_order, 550.0)
        b = compute_point(shuffled, 550.0)
        self.assertNotAlmostEqual(a.reflectance, b.reflectance, places=6)

    def test_transmittance_is_reciprocal(self):
        # Lossless stack: T is the same in both directions.
        stack = Stack(self.air, self.layers, self.glass)
        fwd = compute_point(stack, 550.0)
        bwd = compute_point(stack.reversed(), 550.0)
        self.assertAlmostEqual(fwd.transmittance, bwd.transmittance, places=10)

    def test_energy_conservation_random_stack(self):
        stack = Stack(self.air, self.layers, self.glass)
        for p in compute_spectrum(stack, [400.0, 500.0, 600.0, 700.0]):
            self.assertAlmostEqual(p.energy_residual, 0.0, places=9)

    def test_reversed_is_not_relabelled(self):
        # reversed() must swap media and flip layer order.
        stack = Stack(self.air, self.layers, self.glass)
        rev = stack.reversed()
        self.assertIs(rev.incident, self.glass)
        self.assertIs(rev.substrate, self.air)
        self.assertEqual([l.material.name for l in rev.layers], ["M", "H", "L"])


class WavelengthValidationTests(unittest.TestCase):
    def test_duplicate_wavelengths_rejected(self):
        stack = Stack(const("a", 1.0), (), const("b", 1.5))
        with self.assertRaises(ValueError):
            compute_spectrum(stack, [500.0, 500.0])

    def test_invalid_wavelengths_rejected(self):
        stack = Stack(const("a", 1.0), (), const("b", 1.5))
        for bad in (0.0, -1.0, float("nan"), float("inf"), "x"):
            with self.assertRaises(ValueError):
                compute_spectrum(stack, [bad])


if __name__ == "__main__":
    unittest.main()

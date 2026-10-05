import math
import unittest

from thinfilm.materials import ConfigError, Material
from thinfilm.solver import Layer, Stack, solve_point, solve_stack

AIR = Material.from_json("air", 1.0)
GLASS = Material.from_json("glass", 1.5)
HIGH = Material.from_json("high", 2.3)


def stack(layers=(), incident=AIR, substrate=GLASS):
    return Stack(incident=incident, substrate=substrate, layers=tuple(layers))


class SingleInterfaceTests(unittest.TestCase):
    def test_bare_interface_matches_fresnel(self):
        # Empty layer stack degenerates to a single interface.
        point = solve_point(stack(), 550.0)
        r_expected = ((1.0 - 1.5) / (1.0 + 1.5)) ** 2
        self.assertAlmostEqual(point.reflectance, r_expected, places=12)
        self.assertAlmostEqual(point.transmittance, 1.0 - r_expected, places=12)
        self.assertAlmostEqual(point.energy_residual, 0.0, places=12)

    def test_zero_thickness_layer_is_invisible(self):
        layer = Layer(material=HIGH, thickness_nm=0.0)
        bare = solve_point(stack(), 550.0)
        with_zero = solve_point(stack([layer]), 550.0)
        self.assertAlmostEqual(bare.reflectance, with_zero.reflectance, places=15)
        self.assertAlmostEqual(bare.transmittance, with_zero.transmittance, places=15)


class QuarterWaveTests(unittest.TestCase):
    def test_quarter_wave_ar_coating(self):
        # n_f = sqrt(n0*ns), d = lambda/(4 n_f) -> zero reflectance.
        n_f = math.sqrt(1.0 * 1.5)
        lam = 550.0
        layer = Layer(material=Material.from_json("ar", n_f),
                      thickness_nm=lam / (4.0 * n_f))
        point = solve_point(stack([layer]), lam)
        self.assertAlmostEqual(point.reflectance, 0.0, places=12)
        self.assertAlmostEqual(point.transmittance, 1.0, places=12)

    def test_quarter_wave_high_index_matches_formula(self):
        # Single quarter-wave layer: R = ((n0 ns - nf^2)/(n0 ns + nf^2))^2.
        lam = 600.0
        n_f = 2.3
        layer = Layer(material=Material.from_json("hi", n_f),
                      thickness_nm=lam / (4.0 * n_f))
        point = solve_point(stack([layer]), lam)
        expected = ((1.0 * 1.5 - n_f**2) / (1.0 * 1.5 + n_f**2)) ** 2
        self.assertAlmostEqual(point.reflectance, expected, places=12)

    def test_half_wave_layer_is_absentee(self):
        lam = 500.0
        n_f = 2.0
        layer = Layer(material=Material.from_json("hw", n_f),
                      thickness_nm=lam / (2.0 * n_f))
        point = solve_point(stack([layer]), lam)
        bare = solve_point(stack(), lam)
        self.assertAlmostEqual(point.reflectance, bare.reflectance, places=12)


class AsymmetricStackTests(unittest.TestCase):
    def test_reverse_satisfies_reciprocity_for_asymmetric_stack(self):
        # Lossless reciprocal stacks: R and T are identical from both
        # directions even when the layer order is asymmetric.
        layers = [
            Layer(material=HIGH, thickness_nm=80.0),
            Layer(material=Material.from_json("low", 1.38), thickness_nm=120.0),
        ]
        fwd = solve_point(stack(layers), 550.0)
        rev = solve_point(stack(layers).reversed(), 550.0)
        self.assertAlmostEqual(fwd.reflectance, rev.reflectance, places=12)
        self.assertAlmostEqual(fwd.transmittance, rev.transmittance, places=12)
        self.assertAlmostEqual(fwd.energy_residual, 0.0, places=12)
        self.assertAlmostEqual(rev.energy_residual, 0.0, places=12)

    def test_reverse_is_not_relabeling(self):
        # The reversed computation must really reverse the layer order:
        # reversing a stack differs from reversing its order-swapped twin.
        layers = [
            Layer(material=HIGH, thickness_nm=80.0),
            Layer(material=Material.from_json("low", 1.38), thickness_nm=120.0),
        ]
        swapped = list(reversed(layers))
        rev_a = solve_point(stack(layers).reversed(), 550.0)
        rev_b = solve_point(stack(swapped).reversed(), 550.0)
        self.assertGreater(abs(rev_a.reflectance - rev_b.reflectance), 1e-3)

    def test_order_matters(self):
        layers = [
            Layer(material=HIGH, thickness_nm=80.0),
            Layer(material=Material.from_json("low", 1.38), thickness_nm=120.0),
        ]
        swapped = list(reversed(layers))
        a = solve_point(stack(layers), 550.0)
        b = solve_point(stack(swapped), 550.0)
        self.assertGreater(abs(a.reflectance - b.reflectance), 1e-3)

    def test_symmetric_media_reverse_matches_forward(self):
        # With identical media on both sides, R is direction-independent.
        layers = [
            Layer(material=HIGH, thickness_nm=95.0),
            Layer(material=Material.from_json("low", 1.45), thickness_nm=130.0),
        ]
        s = stack(layers, incident=AIR, substrate=Material.from_json("air2", 1.0))
        fwd = solve_point(s, 550.0)
        rev = solve_point(s.reversed(), 550.0)
        self.assertAlmostEqual(fwd.reflectance, rev.reflectance, places=12)
        self.assertAlmostEqual(fwd.transmittance, rev.transmittance, places=12)


class DispersionTests(unittest.TestCase):
    def test_linear_interpolation(self):
        mat = Material.from_json(
            "bk7", {"wavelengths_nm": [400.0, 700.0], "n": [1.53, 1.51]}
        )
        self.assertAlmostEqual(mat.index_at(400.0), 1.53)
        self.assertAlmostEqual(mat.index_at(550.0), 1.52)
        self.assertAlmostEqual(mat.index_at(700.0), 1.51)

    def test_no_extrapolation(self):
        mat = Material.from_json(
            "bk7", {"wavelengths_nm": [400.0, 700.0], "n": [1.53, 1.51]}
        )
        with self.assertRaises(ConfigError):
            mat.index_at(399.9)
        with self.assertRaises(ConfigError):
            mat.index_at(700.1)

    def test_constant_material_ignores_range(self):
        self.assertEqual(AIR.index_at(100.0), 1.0)
        self.assertEqual(AIR.index_at(5000.0), 1.0)

    def test_table_must_be_strictly_increasing(self):
        with self.assertRaises(ConfigError):
            Material.from_json(
                "bad", {"wavelengths_nm": [400.0, 400.0], "n": [1.5, 1.6]}
            )

    def test_dispersive_stack_energy(self):
        bk7 = Material.from_json(
            "bk7", {"wavelengths_nm": [400.0, 700.0], "n": [1.53, 1.51]}
        )
        s = stack([Layer(material=bk7, thickness_nm=110.0)])
        for point in solve_stack(s, [400.0, 550.0, 700.0]):
            self.assertAlmostEqual(point.energy_residual, 0.0, places=12)


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from thinfilm import Material
from thinfilm.config import ConfigError, load_config
from thinfilm.materials import MaterialError


class MaterialTests(unittest.TestCase):
    def test_constant_any_wavelength(self):
        m = Material.from_constant("air", 1.0)
        self.assertEqual(m.index_at(200.0), 1.0)
        self.assertEqual(m.index_at(2000.0), 1.0)

    def test_table_linear_interpolation(self):
        m = Material.from_table("x", [(400.0, 2.0), (600.0, 3.0)])
        self.assertAlmostEqual(m.index_at(500.0), 2.5)
        self.assertAlmostEqual(m.index_at(400.0), 2.0)
        self.assertAlmostEqual(m.index_at(600.0), 3.0)

    def test_table_no_extrapolation(self):
        m = Material.from_table("x", [(400.0, 2.0), (600.0, 3.0)])
        with self.assertRaises(MaterialError):
            m.index_at(399.9)
        with self.assertRaises(MaterialError):
            m.index_at(600.1)

    def test_table_must_be_strictly_increasing(self):
        with self.assertRaises(MaterialError):
            Material.from_table("x", [(500.0, 2.0), (500.0, 2.1)])
        with self.assertRaises(MaterialError):
            Material.from_table("x", [(600.0, 2.0), (500.0, 2.1)])

    def test_invalid_indices_rejected(self):
        for bad in (0.0, -1.5, float("nan"), float("inf"), "1.5"):
            with self.assertRaises(MaterialError):
                Material.from_constant("bad", bad)
        with self.assertRaises(MaterialError):
            Material.from_table("bad", [(400.0, 1.5), (500.0, -2.0)])
        with self.assertRaises(MaterialError):
            Material.from_table("bad", [(-400.0, 1.5), (500.0, 2.0)])


def _write(tmp, data):
    path = Path(tmp) / "cfg.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


GOOD = {
    "incident": {"name": "air", "n": 1.0},
    "substrate": {"name": "glass", "n": 1.52},
    "layers": [
        {
            "material": {"name": "TiO2", "table": [[400.0, 2.5], [700.0, 2.2]]},
            "thickness_nm": 60.0,
        },
        {"material": {"name": "MgF2", "n": 1.38}, "thickness_nm": 0.0},
    ],
}


class ConfigTests(unittest.TestCase):
    def test_load_valid_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            stack = load_config(_write(tmp, GOOD))
        self.assertEqual(stack.incident.name, "air")
        self.assertEqual(len(stack.layers), 2)
        self.assertAlmostEqual(stack.layers[0].material.index_at(550.0), 2.35)

    def test_missing_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = {k: v for k, v in GOOD.items() if k != "layers"}
            with self.assertRaises(ConfigError):
                load_config(_write(tmp, bad))

    def test_negative_thickness_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = json.loads(json.dumps(GOOD))
            bad["layers"][0]["thickness_nm"] = -5.0
            with self.assertRaises(ConfigError):
                load_config(_write(tmp, bad))

    def test_material_needs_exactly_one_of_n_or_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = json.loads(json.dumps(GOOD))
            bad["incident"] = {"name": "air", "n": 1.0, "table": [[1.0, 1.0], [2.0, 1.0]]}
            with self.assertRaises(ConfigError):
                load_config(_write(tmp, bad))
            bad["incident"] = {"name": "air"}
            with self.assertRaises(ConfigError):
                load_config(_write(tmp, bad))

    def test_bad_table_rejected_via_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = json.loads(json.dumps(GOOD))
            bad["substrate"] = {"name": "g", "table": [[500.0, 1.5], [500.0, 1.6]]}
            with self.assertRaises(ConfigError):
                load_config(_write(tmp, bad))


if __name__ == "__main__":
    unittest.main()

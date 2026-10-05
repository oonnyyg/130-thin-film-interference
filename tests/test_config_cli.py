import csv
import json
import math
import tempfile
import unittest
from pathlib import Path

from thinfilm.cli import main
from thinfilm.config import parse_config
from thinfilm.materials import ConfigError
from thinfilm.report import evaluate, extrema, optimize_layer


def base_config():
    return {
        "incident": {"name": "air", "n": 1.0},
        "substrate": {"name": "glass", "n": 1.5},
        "layers": [
            {"name": "film", "n": 1.38, "thickness_nm": 100.0},
        ],
        "wavelengths_nm": [400.0, 550.0, 700.0],
    }


class ConfigValidationTests(unittest.TestCase):
    def test_duplicate_wavelengths_rejected(self):
        cfg = base_config()
        cfg["wavelengths_nm"] = [500.0, 500.0]
        with self.assertRaises(ConfigError):
            parse_config(cfg)

    def test_invalid_wavelength_rejected(self):
        for bad in (0.0, -5.0, float("nan"), "550"):
            cfg = base_config()
            cfg["wavelengths_nm"] = [bad]
            with self.assertRaises(ConfigError, msg=f"bad={bad!r}"):
                parse_config(cfg)

    def test_negative_thickness_rejected(self):
        cfg = base_config()
        cfg["layers"][0]["thickness_nm"] = -1.0
        with self.assertRaises(ConfigError):
            parse_config(cfg)

    def test_zero_thickness_allowed(self):
        cfg = base_config()
        cfg["layers"][0]["thickness_nm"] = 0.0
        parse_config(cfg)

    def test_nonpositive_index_rejected(self):
        cfg = base_config()
        cfg["substrate"] = {"name": "bad", "n": 0.0}
        with self.assertRaises(ConfigError):
            parse_config(cfg)

    def test_out_of_table_range_rejected_before_output(self):
        cfg = base_config()
        cfg["layers"][0]["n"] = {
            "wavelengths_nm": [450.0, 650.0],
            "n": [1.40, 1.36],
        }
        parsed = parse_config(cfg)  # 400 nm is outside the table
        with self.assertRaises(ConfigError):
            evaluate(parsed)


class ExtremaTests(unittest.TestCase):
    def test_tie_prefers_shorter_wavelength(self):
        class P:
            def __init__(self, w, r):
                self.wavelength_nm = w
                self.reflectance = r

        points = [P(600.0, 0.1), P(400.0, 0.1), P(500.0, 0.3), P(450.0, 0.3)]
        lo, hi = extrema(points)
        self.assertEqual(lo.wavelength_nm, 400.0)
        self.assertEqual(hi.wavelength_nm, 450.0)


class OptimizeTests(unittest.TestCase):
    def test_finds_quarter_wave_minimum(self):
        n_f = math.sqrt(1.5)
        lam = 550.0
        quarter = lam / (4.0 * n_f)
        cfg = base_config()
        cfg["layers"][0]["n"] = n_f
        cfg["optimize"] = {
            "layer_index": 0,
            "wavelength_nm": lam,
            "candidates_nm": [50.0, quarter, 200.0],
        }
        parsed = parse_config(cfg)
        result = optimize_layer(parsed)
        self.assertEqual(result["best_thickness_nm"], quarter)
        self.assertAlmostEqual(result["best_reflectance"], 0.0, places=12)
        self.assertEqual(parsed.stack.layers[0].thickness_nm, 100.0)

    def test_tie_prefers_thinner_candidate(self):
        lam = 550.0
        n_f = math.sqrt(1.5)
        quarter = lam / (4.0 * n_f)
        cfg = base_config()
        cfg["layers"][0]["n"] = n_f
        cfg["optimize"] = {
            "layer_index": 0,
            "wavelength_nm": lam,
            "candidates_nm": [3.0 * quarter, quarter],
        }
        result = optimize_layer(parse_config(cfg))
        self.assertEqual(result["best_thickness_nm"], quarter)


class CliTests(unittest.TestCase):
    def test_cli_writes_outputs(self):
        cfg = base_config()
        cfg["optimize"] = {
            "layer_index": 0,
            "wavelength_nm": 550.0,
            "candidates_nm": [90.0, 100.0, 110.0],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cfg_path = tmp / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            outdir = tmp / "out"
            self.assertEqual(main([str(cfg_path), "-o", str(outdir)]), 0)
            for name in ("forward.csv", "reverse.csv", "summary.json"):
                self.assertTrue((outdir / name).is_file(), name)
            with open(outdir / "forward.csv", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 3)
            for row in rows:
                r = float(row["reflectance"])
                t = float(row["transmittance"])
                self.assertAlmostEqual(r + t, 1.0, places=9)
            summary = json.loads((outdir / "summary.json").read_text("utf-8"))
            self.assertLess(summary["forward"]["max_abs_energy_residual"], 1e-9)
            self.assertLess(summary["reverse"]["max_abs_energy_residual"], 1e-9)
            self.assertIn("optimization", summary)

    def test_cli_rejects_bad_config_without_partial_output(self):
        cfg = base_config()
        cfg["wavelengths_nm"] = [500.0, 500.0]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cfg_path = tmp / "config.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            outdir = tmp / "out"
            self.assertEqual(main([str(cfg_path), "-o", str(outdir)]), 1)
            self.assertFalse((outdir / "forward.csv").exists())


if __name__ == "__main__":
    unittest.main()

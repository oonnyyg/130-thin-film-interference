import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from thinfilm import Material, Stack
from thinfilm.core import Layer
from thinfilm.optimize import optimize_layer_thickness


def const(name, n):
    return Material.from_constant(name, n)


CONFIG = {
    "incident": {"name": "air", "n": 1.0},
    "substrate": {"name": "glass", "n": 1.52},
    "layers": [
        {"material": {"name": "MgF2", "n": 1.38}, "thickness_nm": 100.0},
        {"material": {"name": "TiO2", "n": 2.3}, "thickness_nm": 55.0},
    ],
}


class CliRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cfg = root / "stack.json"
        self.cfg.write_text(json.dumps(CONFIG), encoding="utf-8")
        self.waves = root / "waves.csv"
        self.waves.write_text("wavelength_nm\n400\n500\n600\n700\n", encoding="utf-8")
        self.out = root / "out"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "thinfilm", *args],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent.parent,
        )

    def test_run_exports_bidirectional_csv_and_summary(self):
        proc = self._run(
            "run", "--config", str(self.cfg),
            "--wavelengths", str(self.waves), "--out-dir", str(self.out),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for name in ("forward.csv", "backward.csv", "summary.json"):
            self.assertTrue((self.out / name).exists())
        with open(self.out / "forward.csv", newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 4)
        for row in rows:
            r, t = float(row["reflectance"]), float(row["transmittance"])
            self.assertAlmostEqual(r + t, 1.0, places=9)
        summary = json.loads((self.out / "summary.json").read_text(encoding="utf-8"))
        for direction in ("forward", "backward"):
            block = summary[direction]
            self.assertTrue(block["energy_check_passed"])
            self.assertLess(block["max_abs_energy_residual"], 1e-9)
            self.assertIn("wavelength_nm", block["reflectance_min"])
            self.assertIn("wavelength_nm", block["reflectance_max"])
        # Lossless stack: forward/backward reflectance agree (physical check
        # that the reversed computation is a real recomputation).
        fwd_r = [float(r["reflectance"]) for r in rows]
        with open(self.out / "backward.csv", newline="", encoding="utf-8") as fh:
            bwd_r = [float(r["reflectance"]) for r in csv.DictReader(fh)]
        for a, b in zip(fwd_r, bwd_r):
            self.assertAlmostEqual(a, b, places=9)

    def test_duplicate_wavelengths_rejected_no_output(self):
        self.waves.write_text("500\n500\n", encoding="utf-8")
        proc = self._run(
            "run", "--config", str(self.cfg),
            "--wavelengths", str(self.waves), "--out-dir", str(self.out),
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("duplicate", proc.stderr)
        self.assertFalse((self.out / "forward.csv").exists())

    def test_invalid_wavelength_rejected(self):
        self.waves.write_text("500\nabc\n", encoding="utf-8")
        proc = self._run(
            "run", "--config", str(self.cfg),
            "--wavelengths", str(self.waves), "--out-dir", str(self.out),
        )
        self.assertEqual(proc.returncode, 2)
        self.assertFalse((self.out / "forward.csv").exists())

    def test_optimize_cli(self):
        proc = self._run(
            "optimize", "--config", str(self.cfg), "--layer", "0",
            "--wavelength", "550", "--candidates", "90,99.63768115942029,110",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertAlmostEqual(result["best_thickness_nm"], 99.63768115942029)


class OptimizeTests(unittest.TestCase):
    def test_finds_quarter_wave_thickness(self):
        n = 1.38
        stack = Stack(
            const("air", 1.0), (Layer(const("MgF2", n), 0.0),), const("glass", 1.52)
        )
        quarter = 550.0 / (4.0 * n)
        candidates = [10.0, quarter, 200.0]
        result = optimize_layer_thickness(stack, 0, 550.0, candidates)
        self.assertAlmostEqual(result.best_thickness_nm, quarter)
        self.assertEqual(result.candidates_evaluated, 3)

    def test_tie_breaks_to_thinner(self):
        # d=0 and d=half-wave give identical reflectance; pick thinner.
        n = 1.38
        half = 550.0 / (2.0 * n)
        stack = Stack(
            const("air", 1.0), (Layer(const("MgF2", n), 0.0),), const("glass", 1.52)
        )
        result = optimize_layer_thickness(stack, 0, 550.0, [half, 0.0])
        self.assertEqual(result.best_thickness_nm, 0.0)

    def test_does_not_mutate_stack(self):
        stack = Stack(
            const("air", 1.0), (Layer(const("MgF2", 1.38), 50.0),), const("glass", 1.52)
        )
        optimize_layer_thickness(stack, 0, 550.0, [10.0, 20.0])
        self.assertEqual(stack.layers[0].thickness_nm, 50.0)


if __name__ == "__main__":
    unittest.main()

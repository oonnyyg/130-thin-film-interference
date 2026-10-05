# Thin-Film Interference Calculator

Normal-incidence reflectance (R) and transmittance (T) of lossless
(non-absorbing) multilayer coatings, computed with the coherent
characteristic (transfer) matrix method. Pure Python standard library —
no external optics software.

## Units and conventions

- Wavelengths and layer thicknesses are in **nanometres (nm)**; thicknesses
  are non-negative.
- Refractive indices are real and positive (no absorption).
- Phase convention: with the `exp(-i*omega*t)` time dependence, a layer of
  thickness `d` and index `n` at vacuum wavelength `lambda0` accumulates the
  propagation phase `delta = 2*pi*n*d/lambda0`, and its characteristic
  matrix is

  ```
  M = [[cos(delta), i*sin(delta)/n],
       [i*n*sin(delta), cos(delta)]]
  ```

  The stack matrix is the ordered product of layer matrices (incident side
  first), so all propagation phases and multiple reflections are preserved;
  interface Fresnel coefficients are never summed directly.
- Amplitude coefficients come from the stack matrix elements with
  `n0`/`ns` the incident/substrate indices. Power transmittance uses the
  admittance ratio: `T = (ns/n0) * |t|^2`, `R = |r|^2`.
- Every wavelength point reports the energy residual `R + T - 1`, which
  must be ~0 for a lossless stack; the summary flags failure instead of
  normalising the error away.

## Configuration (JSON)

```json
{
  "incident":  {"name": "air", "n": 1.0},
  "substrate": {"name": "glass", "n": 1.52},
  "layers": [
    {"material": {"name": "MgF2", "n": 1.38}, "thickness_nm": 99.64},
    {"material": {"name": "TiO2",
                  "table": [[400.0, 2.45], [550.0, 2.35], [700.0, 2.28]]},
     "thickness_nm": 58.5}
  ]
}
```

- Each material has exactly one of `"n"` (positive constant) or `"table"`
  (`[wavelength_nm, index]` pairs with strictly increasing positive
  wavelengths and positive finite indices).
- Table values are linearly interpolated; wavelengths outside the table
  range are **rejected** (no extrapolation). Constant materials are
  unrestricted.
- `layers` is ordered from the incident medium towards the substrate; an
  empty list reduces to the bare incident/substrate interface, and
  zero-thickness layers do not change the result.

## Wavelength CSV

One wavelength (nm) per row; an optional header (`wavelength_nm`) is
skipped. Duplicate, non-numeric, non-positive or non-finite values reject
the whole run — no partial spectra are written.

## CLI

```bash
# Forward + backward spectra and JSON summary
python -m thinfilm run --config examples/stack.json \
    --wavelengths examples/wavelengths.csv --out-dir out

# Single-layer thickness search (does not modify the config)
python -m thinfilm optimize --config examples/stack.json --layer 0 \
    --wavelength 550 --candidates 90,95,99.64,105,110
```

`run` writes `forward.csv`, `backward.csv` and `summary.json` into the
output directory. The backward spectrum is a genuine recomputation with
the two media swapped and the layer order reversed — not a relabelling of
the forward result. The summary reports, per direction, the maximum
absolute energy residual, whether it is within tolerance (1e-9), and the
reflectance min/max positions (ties resolved towards the shorter
wavelength).

`optimize` evaluates every candidate thickness for the chosen layer at the
target wavelength and returns the one with the lowest forward reflectance;
ties are broken towards the thinner candidate.

## Tests

```bash
python -m unittest discover -s tests
```

Coverage includes the bare single interface (Fresnel values), quarter-wave
and half-wave layers, zero-thickness invariance, asymmetric layer order,
bidirectional reciprocity invariants, table interpolation/extrapolation
rules, config/wavelength validation, and the CLI end to end.

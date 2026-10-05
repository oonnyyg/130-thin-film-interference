# thin-film-interference

Normal-incidence reflectance/transmittance calculator for lossless
(absorption-free) multilayer coatings, implemented with the Python
standard library only. No external optics software is used.

## Model and conventions

- **Units**: all thicknesses and wavelengths are in nanometers (nm).
  Thicknesses must be non-negative; wavelengths must be positive.
- **Materials**: each material has a real refractive index `n`, either a
  positive constant or a table `{"wavelengths_nm": [...], "n": [...]}`.
  Table wavelengths must be strictly increasing and positive; indices
  must be positive and finite. Values between table points are linearly
  interpolated; extrapolation outside the table is rejected. Constant
  materials are valid at any wavelength.
- **Phase convention**: a layer of index `n` and thickness `d` at vacuum
  wavelength `lam` carries the propagation phase
  `delta = 2*pi*n*d/lam`. Its characteristic matrix is
  `[[cos d, i sin d / n], [i n sin d, cos d]]`, and the stack matrix is
  the ordered product from the incident side to the substrate. This
  coherent product keeps every layer's phase and all multiple
  reflections; interface reflectances are never summed directly.
- **Power coefficients**: from the field amplitudes,
  `R = |r|^2` and `T = (n_substrate / n_incident) * |t|^2`, which
  accounts for the refractive-index ratio of the two media. Every
  wavelength is checked for `R + T ~= 1` (tolerance 1e-9); a violation
  aborts the run instead of being normalized away.
- **Degenerate cases**: zero-thickness layers carry no phase and leave
  the result unchanged; an empty layer list reduces to the bare
  incident/substrate interface (Fresnel coefficients).
- **Reverse illumination**: the reverse spectrum is computed by swapping
  the two media and reversing the layer order, then re-running the
  matrix product — not by relabeling the forward result. (For lossless
  reciprocal stacks R and T happen to be equal in both directions; only
  the reflection phase differs.)

## Configuration

JSON object with keys:

- `incident`, `substrate`: `{"name": ..., "n": <number|table>}`
- `layers`: ordered list (incident side first) of
  `{"name": ..., "n": <number|table>, "thickness_nm": >= 0}`
- `wavelengths_nm`: non-empty list of distinct positive numbers.
  Duplicates or invalid values reject the whole run; no partial
  spectrum is produced.
- `optimize` (optional): `{"layer_index": i, "wavelength_nm": w,
  "candidates_nm": [...]}` — evaluates the forward reflectance at `w`
  for each candidate thickness of layer `i` and reports the minimum;
  ties resolve to the thinner candidate. The input config is not
  modified.

See `examples/quarter_wave_ar.json`.

## Usage

```
python -m thinfilm config.json -o outdir
```

Outputs in `outdir`:

- `forward.csv`, `reverse.csv`: `wavelength_nm, reflectance,
  transmittance, energy_residual` per wavelength.
- `summary.json`: energy residuals and reflectance extrema for both
  directions (ties resolve to the shorter wavelength), plus the
  optimization result when requested.

## Tests

```
python -m unittest discover -s tests
```

Covers the bare single interface (Fresnel), quarter-wave and half-wave
layers, asymmetric layer order vs. reversed illumination, dispersion
interpolation/rejection of extrapolation, config validation, extrema
tie-breaking, and the thickness optimizer.

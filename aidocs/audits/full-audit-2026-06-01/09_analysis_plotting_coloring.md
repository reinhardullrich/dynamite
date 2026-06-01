# 09 Analysis, Plotting, and Coloring Audit

Scope: post-run analysis helpers in `dynamite/analysis.py`, plotting helpers in
`dynamite/plotter.py`, and population/coloring helpers in
`dynamite/coloring.py`.

These modules mostly consume completed model outputs. They still matter for a
full audit because they can recompute derived science products, select the best
model, create cache files, and produce figures used for interpretation.

## Findings

### APC-001 - High - `Decomposition.plot_decomp()` divides a Python list by a scalar

Evidence:

- `dynamite/analysis.py:269-287` builds `t` as a Python list of arrays.
- `dynamite/analysis.py:303` executes `t = t/totalf`.

Impact:

This raises `TypeError` before the decomposition plot/table can be written.
The failure is deterministic for this path once `plot_decomp()` reaches that
line.

Recommended fix:

Convert `t` to a NumPy array before normalization, and guard `totalf > 0`.

### APC-002 - Medium - decomposition plotting has multiple zero/empty reductions

Evidence:

- `dynamite/analysis.py:281-291` divides component flux by pixel-bin counts,
  normalizes by `np.sum(tt)`, then takes `np.nanmin/np.nanmax` over
  `tt[tt != 0]`.
- `dynamite/analysis.py:293-294` reduces only positive sigma values.

Impact:

Components with zero weights, empty bins, or no positive sigma values can
produce divide-by-zero warnings or empty-slice reduction errors. This is likely
for sparse components and failed/partial model outputs.

Recommended fix:

Add explicit empty and zero-total guards per component. Record unavailable
component maps as masked arrays or `NaN` with a warning instead of failing in
uncontrolled reductions.

### APC-003 - Medium - decomposition cache conversion assumes compatible component lists

Evidence:

- `dynamite/analysis.py:113-127` reads cached component metadata.
- `dynamite/analysis.py:123-125` iterates over `self.comps` and indexes
  `c_file[i]` without validating that `c_file` is the same length and semantic
  order.

Impact:

A stale or malformed `decomp_table.ecsv` cache can raise `IndexError` or
silently rewrite component labels incorrectly.

Recommended fix:

Validate cached metadata schema and length before converting. If the cache is
not exactly compatible, recompute the decomposition.

### APC-004 - Medium - orbit decomposition can fail when the most massive early orbit exceeds half the total weight

Evidence:

- `dynamite/analysis.py:550-555` computes
  `np.max(np.ravel(np.where(np.cumsum(orbw[t]) <= 0.5)))`.

Impact:

If no cumulative-weight element is `<= 0.5`, the reduction is over an empty
array. This can happen when weights are not normalized to total one or when the
first sorted orbit dominates.

Recommended fix:

Normalize or explicitly compute the half-mass threshold, then handle the empty
selection case.

### APC-005 - High - orbit-bundle map normalization can leave uninitialized values

Evidence:

- `dynamite/analysis.py:784-790` calls `np.divide(..., where=...)` without an
  initialized `out` array.

Impact:

For apertures where `flux_all == 0`, NumPy leaves the corresponding output
entries uninitialized when no `out` is supplied. That can put arbitrary values
into a normalized flux table and any downstream plot.

Recommended fix:

Use an initialized output array:

```python
out = np.zeros_like(flux, dtype=float)
flux = np.divide(flux, flux_all[np.newaxis, :], out=out,
                 where=flux_all[np.newaxis, :] != 0)
```

### APC-006 - Medium - surface-brightness map log masking is incorrect

Evidence:

- `dynamite/analysis.py:820-825` divides by `bin_mult`, then uses
  `np.log10(flux, where=flux is not np.nan)`.
- `dynamite/plotter.py:857-862` uses the same `where=array is not np.nan`
  pattern for flux plots.

Impact:

`flux is not np.nan` is a scalar identity check, not an element-wise finite
mask. It does not prevent invalid log operations. The preceding division by
`bin_mult` can also divide by zero for empty aperture bins.

Recommended fix:

Use element-wise masks such as `np.isfinite(flux) & (flux > 0)`, and initialize
the output array before calling `np.log10(..., out=..., where=mask)`.

### APC-007 - Medium - Rmax/zmax plot fails for selected components

Evidence:

- `dynamite/plotter.py:2455-2456` builds `comp_map` as a Python list.
- `dynamite/plotter.py:2460` and `2463` use `comp_map & (model.weights > 0)`.

Impact:

When `components != 'all'`, this can raise `TypeError` because `comp_map` is a
list, not a NumPy boolean array. The component-specific branch of
`rmax_zmax_plot()` is therefore fragile.

Recommended fix:

Convert `comp_map = np.array(comp_map, dtype=bool)` before using boolean array
operations. Also guard empty positive-weight selections before `np.min` and
`np.max`.

### APC-008 - Medium - best-model lookup by chi-square value is ambiguous

Evidence:

- `dynamite/plotter.py:163-168` finds a row by matching chi-square values.
- `dynamite/plotter.py:444-452` finds the minimum chi-square, adds an index on
  that value, and resolves the model by value.

Impact:

If multiple model rows share the same chi-square, the selected row may be
ambiguous. This is less robust than using stable model IDs or the existing
`AllModels.get_best_n_models_idx()` helper consistently.

Recommended fix:

Select by table row/model ID, not by floating-point chi-square value.

### APC-009 - Medium - coloring cache metadata can become inconsistent with cache arrays

Evidence:

- `dynamite/coloring.py:395-400` writes YAML metadata before saving the `.npz`
  bundle data.
- `dynamite/coloring.py:626-630` repeats the same pattern in the PowerBin path.

Impact:

If `np.savez()` fails after metadata is written, later runs may find metadata
that points to a missing or incomplete cache file.

Recommended fix:

Write the `.npz` file first to a temporary name, atomically replace it, then
update metadata. Use the same approach for metadata writes.

### APC-010 - Medium - empty YAML metadata crashes cache iteration

Evidence:

- `dynamite/coloring.py:220-226` and `484-490` assign
  `bundle_metadata = yaml.safe_load(f)`.
- The code then iterates over `bundle_metadata` without normalizing `None` to
  an empty list.

Impact:

An empty `voronoi_orbit_bundles.yaml` file makes `yaml.safe_load()` return
`None`, causing a `TypeError` during cache lookup.

Recommended fix:

Use `bundle_metadata = yaml.safe_load(f) or []` and validate that the result is
a list of dictionaries.

### APC-011 - Medium - phase-space binning densifies sparse projection tensors

Evidence:

- `dynamite/coloring.py:355-356` calls `orbit_projection.todense()` before
  reshaping and multiplying by model weights.
- `dynamite/coloring.py:585-586` does the same in the PowerBin path.

Impact:

For large orbit grids, this can consume far more memory than necessary. The
repository targets scientific workloads where model size can grow quickly.

Recommended fix:

Keep the projection tensor sparse as long as possible or process one bin/bundle
block at a time.

### APC-012 - Medium - Bayesian coloring fits are not reproducible by default

Evidence:

- `dynamite/coloring.py:745-749` calls `pm.sample()` without an explicit
  `random_seed`, chain count, core count, or sampler diagnostics policy.

Impact:

Repeated population/coloring fits can produce different posterior samples even
when the model outputs are unchanged. That is a problem for audit and
regression runs.

Recommended fix:

Expose a sampling configuration that includes `random_seed`, `chains`,
`cores`, `target_accept`, and a required posterior diagnostic summary.

### APC-013 - Low - invalid escape sequences remain in docstrings/labels

Evidence:

`python -Wall -m py_compile dynamite/coloring.py dynamite/physical_system.py`
reports invalid escape sequence warnings in `coloring.py` lines 71, 130, 523,
761, 864, 981, 1173, 1347, 1385, and `physical_system.py:1516`.

Impact:

These do not currently prevent import, but they create noise in strict warning
runs and future Python versions may treat more warning categories strictly.

Recommended fix:

Use raw strings for docstrings and labels containing LaTeX backslashes, or
escape the backslashes.

## Local Status

The analysis/plotting/coloring audit was static plus compile-warning based. No
source files were modified and no model-output analysis was executed because a
complete sample model run was not part of this audit stage.

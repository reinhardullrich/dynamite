# 09 Analysis, Plotting, and Coloring Audit

Audit date: 2026-06-04

## Scope

`dynamite/analysis.py`, `dynamite/plotter.py`, `dynamite/coloring.py`, and
related plotting/cache outputs.

## Findings

### APC-001 - `Decomposition.plot_decomp()` still divides a Python list by a scalar

Severity: High for that workflow.

Evidence:

- `analysis.py` builds `t = []`, appends arrays, then executes `t = t/totalf`.

Impact: this path raises `TypeError` before plotting can complete.

Recommendation: convert to a NumPy array or normalize each component array
explicitly.

### APC-002 - Decomposition plotting still has empty/zero reduction risks

Severity: Medium.

Evidence:

- flux ranges use `np.nanmin(np.log10(tt[tt != 0]))`;
- sigma ranges use positive-only masks;
- empty masks can raise or produce invalid plot limits.

Recommendation: add explicit empty/zero handling and tests with zero-flux
components.

### APC-003 - Flux normalization can leave uninitialized values

Severity: Medium/High.

Evidence:

- `analysis.py` uses `np.divide(flux, flux_all[np.newaxis, :],
  where=flux_all[np.newaxis, :] != 0)` without `out=`.

Impact: entries where `where` is false can contain uninitialized memory.

Recommendation: pass an initialized `out=np.zeros_like(flux, dtype=float)`.

### APC-004 - Plotting still contains invalid `np.log10(..., where=...)` masks

Severity: Medium.

Evidence:

- `plotter.py` uses expressions like `np.log10(flux_plot,
  where=flux_plot is not np.nan)`, which is scalar identity logic, not an
  elementwise finite mask.
- similar pattern exists for `fluxm_plot`.

Recommendation: use `np.isfinite()` and positive-value masks with initialized
`out`.

### APC-005 - Best-model lookup by chi-square value is ambiguous

Severity: Medium.

Evidence:

- plotting paths derive `model_id` through equality on chi-square values.

Impact: ties or duplicate chi-square values can select the wrong model.

Recommendation: use `AllModels.get_best_n_models_idx()` or explicit row ids.

### APC-006 - Coloring metadata can become inconsistent or crash on empty YAML

Severity: Medium.

Evidence:

- `coloring.py` reads `voronoi_orbit_bundles.yaml` via `yaml.safe_load()`.
- Empty YAML returns `None`, but code then iterates over `bundle_metadata`.
- metadata and `.npz` arrays are written separately.

Recommendation: normalize empty metadata to `[]`; write metadata/cache files
atomically and validate referenced `.npz` files before reuse.

### APC-007 - Bayesian/coloring smoothing lacks explicit reproducibility contract

Severity: Medium.

Evidence:

- coloring uses random sampling for smoothing. There is no clearly persisted
  seed/settings record that makes the exact coloring output reproducible.

Recommendation: add explicit seed input, store seed and parameters in output
metadata, and test deterministic repeated runs.

### APC-008 - VorBin deprecation warning is current

Severity: Low/Medium.

Observed warning:

- importing `dynamite/coloring.py` warns that VorBin is deprecated and should
  be replaced by PowerBin.

Recommendation: plan migration or pin/document VorBin as a known deprecated
dependency.

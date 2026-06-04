# Full Audit Summary

Audit date: 2026-06-04
Audited state: current `Fortran-cleanup` working tree, including uncommitted
PF-01, PF-02, and PF-03 Fortran performance changes.

## Executive Result

This audit keeps only findings that matter for the current working tree. The
highest-risk items are around state mutation, scientific validation, and
operational robustness.

## Verification Completed

Commands passed on 2026-06-04:

- `.venv/bin/python -m pip check`
- `.venv/bin/python -m compileall -q dynamite tests`
- `make -C orblib_fortran shared`
- `git diff --check`
- `.venv/bin/python -m pytest` -> 62 passed, 6 skipped
- `DYNAMITE_RUN_SLOW_TESTS=1 DYNAMITE_RUN_ORBLIB_FORTRAN_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_orblib_output.py tests/test_fortran_inventory.py` -> 11 passed

Current warnings:

- `dynamite/coloring.py` imports deprecated VorBin.
- `pip check` emitted only the local pip-cache ownership warning.

## Highest-Priority Current Findings

### 1. Configuration and model-state constructors still mutate output state

Evidence:

- `Configuration(..., reset_existing_output=True)` deletes the configured
  output directory tree.
- `Configuration.__init__()` updates orbit-library flags and saves
  `all_models.ecsv` through `AllModels.update_model_table()`.
- explicit cleanup helpers still remove model trees, weight directories, plot
  files, all-models files, and cached input products.

Priority: high. The behavior may be intended, but it is still not cleanly
separated from read-only configuration parsing.

### 2. `all_models.ecsv`, caches, and model output writes are not atomic

Evidence:

- `AllModels.save()` writes directly to the final ECSV path with
  `overwrite=True`.
- cache/result files in modeling, coloring, plotting, and NNLS paths are often
  written directly to final locations.
- model pruning and cleanup use recursive deletes for model/orbit-library
  directories.

Priority: high for long runs and interrupted runs.

### 3. Solver result validation is still incomplete

Evidence:

- SciPy and CVXOPT solver exceptions are converted to NaN weights, but the
  active `NNLS.solve()` path checks only `np.isnan(weights[0])` before computing
  chi-square and writing output.
- There is no explicit `SolverProblem` / `SolverResult` object with solver
  status, finite checks, non-negativity checks, matrix/rhs shape metadata, and
  residual diagnostics.
- CVXOPT stores `success`, but `NNLS.solve()` uses only `solver.beta`.

Priority: high for scientific result acceptance.

### 4. Physical and data-domain validation remains incomplete

Evidence:

- logarithmic `Parameter` values transform through `10.**raw_value` and
  `np.log10(par_value)` without central finite/positive validation;
- `System.validate_parset()` skips negative-domain checks for logarithmic
  parameters;
- several physical-system accessors still use `assert`, which can be disabled
  under optimized Python;
- active data readers and transformations do not consistently require finite
  values at every boundary.

Priority: high/medium depending on parameter path.

### 5. Model/orbit-library identity uses tolerance-based matching

Evidence:

- `ParameterGenerator._is_newmodel()`, `AllModels.get_model_from_parset()`,
  `get_row_from_model()`, `get_ml_of_original_orblib()`, pruning, and
  chi-square duplicate logic use `np.allclose()`.

Priority: medium/high. This is convenient numerically but can conflate close
but distinct models and should be replaced by explicit stable keys.

### 6. Plotting, analysis, and coloring still contain deterministic runtime risks

Examples:

- `Decomposition.plot_decomp()` builds `t` as a Python list and later executes
  `t = t/totalf`.
- flux normalization in `Analysis.get_...` style code uses `np.divide(...,
  where=...)` without an initialized `out`.
- plotting code still contains invalid `np.log10(..., where=flux_plot is not
  np.nan)`-style scalar identity masks.
- coloring metadata reads can return `None` for empty YAML and then iterate over
  it.
- Bayesian/coloring smoothing uses random sampling without a clear persisted
  deterministic seed contract.

Priority: medium/high for workflows using those tools.

## Recommended Next Actions

1. Separate read-only configuration parsing from output mutation:
   - no deletion, all-models repair, flag repair, or model pruning from plain
     construction unless a clearly named mutation mode is requested.

2. Add atomic writes:
   - write ECSV/NPZ/YAML/cache files to temp paths;
   - `os.replace()` only after validation;
   - keep model completion markers as final-stage artifacts.

3. Formalize solver contracts:
   - add `SolverProblem` and `SolverResult`;
   - fail hard on non-finite weights, negative weights, non-finite chi-square,
     wrong shapes, or failed backend status.

4. Replace tolerance-based model matching with stable keys:
   - `model_key` for full parameter identity;
   - `orblib_key` for parameters that define reusable orbit libraries.

5. Add domain validators:
   - central finite/positive checks for logarithmic parameters;
   - physical-domain checks for dark-halo and viewing parameters;
   - hard errors before backend launch.

6. Add rotating-frame scientific fixtures:
   - current PF-01/PF-03 preservation of `Omega /= 0` behavior is structurally
     careful, but not regression-tested against real rotating-frame outputs.

## Current Worktree Notes

The audit includes the current uncommitted `Fortran-cleanup` working tree.

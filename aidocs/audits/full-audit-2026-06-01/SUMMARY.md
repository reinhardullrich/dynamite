# Full Audit Summary

Date: 2026-06-01

Repository: `/home/reinhard/projects/thomas/dynamite`

## Verification Completed

Local-only setup was used.

- Python virtualenv created in `.venv/`.
- Editable install with testing extras completed:
  `.venv/bin/python -m pip install --no-cache-dir --no-build-isolation -e ".[testing]"`.
- `pip check` passed.
- Core imports succeeded for DYNAMITE, NumPy, SciPy, Astropy, and Matplotlib.
- Python compile check passed for `dynamite/`.
- GNU Fortran 13.3.0 is available locally.
- `make nogal` succeeded in `legacy_fortran/`.
- Local GALAHAD 2.3 QP installation completed using the vendored
  `legacy_fortran/galahad-2.3`, `cuter`, and `hsl` trees.
- Full GALAHAD-backed `make all` succeeded after repairing two generated static
  archives that were missing `gltr.o` and `hsl_ma57d.o`.
- GALAHAD-linked `triaxnnls_*` binaries passed link/load checks with no missing
  dynamic libraries and no unresolved GALAHAD/HSL symbol matches.
- A temporary real-model legacy run in `/tmp/dynamite-galahad-run` completed 5
  classic NNLS weight solves with exit code 0.
- Direct solver-mode `5` GALAHAD/QPB probes reached `QPB_solve` for both
  `triaxnnls_noCRcut` and `triaxnnls_CRcut`.
- Pytest collection was attempted and failed before collecting tests.

## Highest-Priority Findings

### 1. CI does not test the real package or the pytest suite

CI installs `requirements.txt` but does not install this `setup.py` package
unless a `pyproject.toml` exists. It also comments out pytest and directly runs
only `dev_tests/test_nnls.py`.

Local pytest collection currently fails due to:

- missing `dynamite.data_prep.data_prep_test`;
- cwd-sensitive import-time config loading in `dev_tests/test_decomp.py`.

Priority: high.

### 2. Runtime constructors and development tests can mutate or delete output state

`Configuration` and development scripts can update output state or reset output
directories during construction/top-level execution. This makes imports and
test collection unsafe around existing model outputs.

Priority: high.

### 3. Python-to-Fortran failure detection is too weak

Several wrappers infer success from stdout or marker files instead of enforcing
subprocess return codes, required output files, and file-shape validation.
Generated scripts also need stricter failure handling.

Priority: high.

### 4. Solver outputs need full validation

Solver paths do not consistently validate convergence status, all finite
weights, non-negative weights, finite chi-square values, and required output
dimensions. This is now confirmed at runtime for GALAHAD: direct solver-mode
`5` runs reached QPB, logged `QPB_solve exit status = -5`, then still exited
with shell status `0` and wrote downstream output files.

Priority: high.

### 5. Physical parameter domains are not enforced strongly enough

Logarithmic parameters can be transformed before positive-domain validation.
Several dark-halo and barred-component validation paths are incomplete or
broken if called. Invalid physical inputs can reach numerical backend code.

Priority: high.

### 6. Model state can be corrupted by non-atomic writes or chi-square retry bugs

`all_models.ecsv` and cache files are written directly to final paths. The
external chi-square retry path likely double-counts totals in some cases, and
one table update writes `chi2_ext` to a whole column instead of the current row.

Priority: high.

### 7. Analysis/plotting contains deterministic runtime bugs

Examples:

- `Decomposition.plot_decomp()` divides a Python list by a scalar.
- normalized flux output can contain uninitialized values when using
  `np.divide(..., where=...)` without `out`.
- component-specific Rmax/zmax plots use a Python list in NumPy boolean logic.

Priority: high/medium depending on workflow.

## Medium-Priority Findings

- Full GALAHAD/legacy solver build is fragile: the vendored dependency trees
  are present, but the local GALAHAD installer left required objects out of
  generated static archives under GNU Fortran 13.3.0.
- Default Fortran flags use `-ffast-math` and `-march=native`, reducing
  reproducibility and portability.
- Orbit-library reuse and model lookup use default `np.allclose()` matching,
  which can conflate close but distinct parameter rows.
- Numerical integration warnings are logged/printed but not recorded as model
  quality metadata.
- Coloring/cache metadata can point to missing `.npz` files after interrupted
  writes.
- Bayesian coloring fits do not expose deterministic sampling seeds.
- Several data-boundary validations rely on `assert` or lack full finite-value
  checks.
- Matplotlib needs an explicit writable `MPLCONFIGDIR` in this local/sandboxed
  environment.
- Dependencies are locally installed but not locked, so future audit runs can
  drift.

## Recommended Next Actions

1. Make CI honest:
   - install with `.venv/bin/python -m pip install -e ".[testing]"`;
   - run pytest collection;
   - split fast tests from slow/destructive model-generation tests.

2. Harden execution boundaries:
   - check subprocess return codes;
   - add `set -e` to generated scripts;
   - validate required output files before marking runs complete.

3. Harden solver result validation:
   - require finite/non-negative full weight arrays;
   - require finite chi-square values;
   - make non-zero solver statuses explicit failure states.

4. Separate read-only configuration from destructive output repair/reset.

5. Add domain validation before parameter transforms and backend launch.

6. Make model-state writes atomic and fix external chi-square retry/update
   logic.

7. Convert the current script-like `dev_tests/` into pytest-compatible tests
   with temporary output directories.

8. Add a reproducible audit environment:
   - keep `.venv/` local;
   - prefer `uv` for future fresh setup if desired;
   - record/lock package versions for repeatable audits.

## Improvement Roadmap

The improvement-focused continuation is recorded in
`14_improvement_opportunities.md`. It intentionally avoids bug-fix work and
focuses on making the existing system faster, smoother, shorter, and easier to
develop.

Highest-payoff improvement themes:

0. Keep runtime expectations realistic:
   - local `import dynamite` takes about 3.6 seconds, so startup matters for
     short tools and test collection;
   - full legacy model runs are dominated by Fortran orbit-library generation
     and surrounding disk I/O, not import time.

1. Reduce hot-path text I/O:
   - keep ECSV for inspection/export;
   - use binary sidecars for large runtime arrays, weights, mass grids, and
     cacheable solver inputs.

2. Cache prepared solver inputs:
   - cache NNLS matrix blocks by orbit-library/settings/input hash;
   - avoid rebuilding identical matrix components for repeated solves.

3. Speed table lookups:
   - create stable `model_key` and `orblib_key` values;
   - replace repeated full-table scans with dictionary lookups.

4. Make runtime stages explicit:
   - separate config parsing from output mutation;
   - add per-stage timing manifests;
   - move shell command generation toward structured command specs.

5. Make imports lighter for developer ergonomics:
   - reduce eager imports from `dynamite/__init__.py`;
   - avoid pulling plotting/coloring/PyMC dependencies into every basic import.

6. Make the code shorter and easier to modify:
   - extract large methods into stage-specific helpers;
   - introduce typed settings wrappers incrementally;
   - add a small public workflow API for validate/plan/run/resume/summarize.

7. Treat Python `NNLS` as the modern solver path:
   - keep legacy Fortran/GALAHAD as compatibility and parity-reference backend;
   - introduce a common `SolverProblem` / `SolverResult` interface;
   - add parity checks before changing defaults;
   - evaluate `scipy.lsq_linear` and sparse/iterative approaches only after
     matrix density and memory use are measured.

## Local Worktree Status

Expected new local documentation:

- `AGENTS.md`
- `aidocs/`

Expected ignored local/generated state:

- `.venv/`
- `.pytest_cache/`
- Python `__pycache__/`
- Fortran `.o/.mod` files
- no-GALAHAD Fortran executables built under `legacy_fortran/`
- GALAHAD Fortran build artifacts under `legacy_fortran/galahad-2.3/`
- full legacy Fortran executables built under `legacy_fortran/`

No upstream `docs/`, package source under `dynamite/`, Fortran source under
`legacy_fortran/`, or development test files under `dev_tests/` were edited
during this audit stage.

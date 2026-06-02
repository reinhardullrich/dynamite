# Full Audit Summary

Date: 2026-06-01

Repository: `/home/reinhard/projects/thomas/dynamite`

Current-status update: this summary has been adapted for the
`fortran-cleanup` branch as of 2026-06-02. The original audit evidence remains
useful for risk analysis, but several build/test/backend findings are now
resolved or superseded by the direct shared-library orbit backend and current
pytest baseline.

## Verification Completed

Current local verification baseline for the `fortran-cleanup` branch:

- Python virtualenv created in `.venv/`.
- Editable install with testing extras completed:
  `.venv/bin/python -m pip install --no-cache-dir --no-build-isolation -e ".[testing]"`.
- `pip check` passed.
- Core imports succeeded for DYNAMITE, NumPy, SciPy, Astropy, and Matplotlib.
- Python compile check passed for `dynamite/`.
- GNU Fortran 13.3.0 is available locally.
- The active Fortran build is shared-library-only under `orblib_fortran/` and
  writes `orblib_fortran/build/lib/liborblib_fortran.so`.
- Chapter 13 now records the active runtime verification contract for the
  shared-library build, direct Python-input API, binary `datfil/` outputs,
  Python `NNLS`, and current pytest coverage.
- Current pytest coverage exists under `tests/`; focused fast tests and opt-in
  slow orblib shared-library LOSVD tests passed during the cleanup.

## Highest-Priority Findings

### 1. CI does not test the real package or the pytest suite

CI installs `requirements.txt` but does not install this `setup.py` package
unless a `pyproject.toml` exists. It also comments out pytest and directly runs
only `archive/dev_tests/test_nnls.py`.

Original local pytest collection failed due to:

- missing `dynamite.data_prep.data_prep_test`;
- cwd-sensitive import-time config loading in `archive/dev_tests/test_decomp.py`.

Current status: superseded. Old development-test content is archived under
`archive/dev_tests/`, and the active pytest baseline lives under `tests/`.

Priority: resolved for the local cleanup baseline; still useful as upstream CI
guidance.

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
dimensions. The current Python `NNLS` path should make solver input, output,
status, diagnostics, and model-completion validation explicit.

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

7. Maintain the new pytest baseline under `tests/`; the old script-like
   workflows are archived under `archive/dev_tests/`.

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
   - full active model runs are dominated by shared-library orbit-library
     generation and surrounding disk I/O, not import time.

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

7. Make Python `NNLS` an explicit, validated solver contract:
   - introduce a common `SolverProblem` / `SolverResult` interface;
   - add deterministic active solver fixtures;
   - cache prepared matrix blocks only with strict keys;
   - evaluate additional active solver approaches only after matrix density
     and memory use are measured.

## Active Solver Follow-Up

The solver-specific continuation is recorded in
`15_active_nnls_solver_benchmark.md`.

Key result:

- The active weight-solver path is Python `NNLS`.
- `nnls_solver: "scipy"` remains the recommended default for plain
  non-negative least squares.
- CVXOPT remains an optional cross-check backend.
- The next useful benchmark work is to split matrix assembly, solve time,
  chi-square reconstruction, and output writing.

Recommendation:

- keep active configs on `type: "NNLS"` with `nnls_solver: "scipy"` unless
  current-code benchmarks justify a change;
- add `SolverProblem` and `SolverResult` internally;
- add deterministic solver-kernel and matrix-construction fixtures;
- cache prepared matrix blocks only with strict dependency keys.

## Local Worktree Status

Expected new local documentation:

- `AGENTS.md`
- `aidocs/`

Expected ignored local/generated state:

- `.venv/`
- `.pytest_cache/`
- Python `__pycache__/`
- Fortran `.o/.mod` files
- `orblib_fortran/build/lib/liborblib_fortran.so`

Current cleanup edits intentionally touched package source under `dynamite/`,
Fortran source under `orblib_fortran/`, local tests under `tests/`, and local
AI docs under `aidocs/`. Upstream Sphinx `docs/` remains out of scope unless
explicitly requested.

# 15 NNLS, GALAHAD, and SciPy Solver Benchmark

Date: 2026-06-02

Scope: clarify which weight solvers exist in DYNAMITE, how GALAHAD and the
old Fortran NNLS path are configured, how the Python SciPy/CVXOPT paths are
configured, and what the local benchmark showed.

Current-status update, 2026-06-02: this chapter has been adapted for the
`fortran-cleanup` branch. The recommended direction has been implemented
locally for active runtime: `LegacyWeightSolver` is rejected by configuration
validation and `Model.get_weights()`, and legacy NNLS/GALAHAD sources are
archived under `archive/legacy_nnls_fortran/`. The active solver path is Python
`NNLS`.

This chapter follows up chapter 13, which verified that the local GALAHAD build
can link and reach QPB at runtime, and chapter 14, which proposed treating the
Python `NNLS` path as the future default.

## Executive Conclusion

For plain non-negative least squares weight solving, GALAHAD is not needed.

The benchmark result is clear for the tested NGC6278 models:

- Python `scipy.optimize.nnls` produced the same solution as the old Fortran
  Lawson-Hanson NNLS solver to numerical roundoff.
- Python `scipy.optimize.nnls` was the fastest valid backend in the benchmark.
- CVXOPT is feasible as an optional cross-check backend, but it was slower and
  not quite identical without stricter solver settings.
- GALAHAD/QPB mode `5` failed on all five tested models with
  `QPB_solve exit status = -5`.

Therefore, for new development and normal plain-NNLS runs, the best current
path is:

```yaml
weight_solver_settings:
    type: "NNLS"
    nnls_solver: "scipy"
```

The legacy Fortran/GALAHAD stack is no longer active in this local branch. It
is retained only as archived compatibility/reproducibility material for older
published outputs, older configurations, or additional constrained GALAHAD modes
that are not equivalent to plain NNLS.

## Terminology

The names are easy to confuse, because several layers sit in the same Fortran
programs.

### Legacy Fortran NNLS

This is the old Fortran weight-solving route that used to be exposed by:

```yaml
weight_solver_settings:
    type: "LegacyWeightSolver"
    nnls_solver: 1
```

Python class:

- `dynamite/weight_solvers.py:151`, `LegacyWeightSolver`

Archived Fortran executables:

- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_CRcut`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_bar`

Algorithm:

- Lawson-Hanson non-negative least squares from
  `archive/legacy_nnls_fortran/legacy_fortran/sub/nnls95.f`

Problem:

```text
minimize ||A x - b||^2
subject to x >= 0
```

Here, `x` is the vector of non-negative orbit weights.

This was the benchmark baseline, because it represents the old DYNAMITE NNLS
behavior.

### Python NNLS

This is the modern Python weight-solving route exposed by:

```yaml
weight_solver_settings:
    type: "NNLS"
    nnls_solver: "scipy"
```

Python class:

- `dynamite/weight_solvers.py:592`, `NNLS`

SciPy backend:

- `dynamite/weight_solvers.py:817`, `optimize.nnls(A, b, maxiter=maxiter)`

CVXOPT backend:

- `dynamite/weight_solvers.py:835`, forms `P = A.T @ A` and
  `q = -A.T @ b`, then solves the equivalent non-negative quadratic program.

This path does not use GALAHAD.

### GALAHAD/QPB

GALAHAD is not the plain NNLS solver. It is a broader Fortran optimization
library. In this repository it is used inside the old `triaxnnls_*` programs
through GALAHAD's QPB quadratic-programming package.

The relevant Fortran routine is:

- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:848`,
  `donnls_galahad`

The actual QPB call is:

- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:1144`,
  `CALL QPB_solve(...)`

The Fortran solver menu in `triaxnnls_noCRcut.f90` distinguishes the paths:

```text
(1) NNLS
(2) NNLS and save the matrix to disk to save memory
(5) Least squares with bounds and constraints ConstrainZeroMoment (Preferred)
```

Mode `1` calls the old Lawson-Hanson NNLS route.

Modes `0`, `4`, `5`, and `6` call `donnls_galahad(...)`, which reaches
GALAHAD/QPB.

## Runtime Dispatch in Python

The active solver is selected by config. In the current cleanup branch, the
legacy solver type is rejected rather than silently replaced.

Old dispatch before cleanup:

```python
ws_type = self.config.settings.weight_solver_settings['type']
if ws_type == 'LegacyWeightSolver':
    weight_solver = ws.LegacyWeightSolver(config=self.config, model=self)
elif ws_type == 'NNLS':
    weight_solver = ws.NNLS(config=self.config, model=self)
else:
    raise ValueError(...)
```

Current branch behavior:

- `type: "LegacyWeightSolver"` raises a clear error because the old Fortran
  route is archived.
- `type: "NNLS"` launches the Python route.
- `nnls_solver: "scipy"` uses SciPy.
- `nnls_solver: "cvxopt"` uses CVXOPT.

## Where GALAHAD Is Needed

GALAHAD is needed only if the project builds or runs the full legacy Fortran
solver binaries with GALAHAD/QPB support.

Archived build files:

- `archive/legacy_nnls_fortran/legacy_fortran/Makefile.linux:104` has `all`,
  including the `triaxnnls_*` binaries.
- `archive/legacy_nnls_fortran/legacy_fortran/Makefile.linux:105` had `nogal`,
  which built only the old orbit-library programs and did not build the
  `triaxnnls_*` solver binaries.
- `archive/legacy_nnls_fortran/legacy_fortran/Makefile.linux:266`, `279`, and
  `291` link the
  `triaxnnls_*` binaries against GALAHAD libraries.

Documentation already describes two installation options:

- option A: GALAHAD plus Python NNLS solvers;
- option B: only Python NNLS solvers.

This means the repository already acknowledges that GALAHAD is optional if the
Python `NNLS` path is sufficient.

## Is Legacy Fortran NNLS Still In Use?

No. In the current cleanup branch it is retained only as archived source and is
not selectable by active configuration/model execution.

Archived examples that used `LegacyWeightSolver`:

- `archive/dev_tests/user_test_config.yaml`
- `archive/dev_tests/test_slurm_config.yaml`
- `archive/dev_tests/dif_dm_halos_config.yaml`
- `archive/dev_tests/reimplement_nnls_config1.yaml`

Examples that use the modern Python path:

- `docs/tutorial_notebooks/NGC6278_config.yaml`
- `docs/tutorial_notebooks/NGC6278_config_single.yaml`
- `docs/tutorial_notebooks/FCC167_config.yaml`
- `docs/tutorial_notebooks/NGC4550_config.yaml`
- `archive/dev_tests/user_test_config_ml.yaml`
- `archive/dev_tests/user_test_config_ml_gas.yaml`
- `archive/dev_tests/user_test_config_specificmodels.yaml`
- `archive/dev_tests/reimplement_nnls_config2.yaml`
- `archive/dev_tests/bayes_losvd/IC0719_dynamite_config.yaml`

The docs and runtime validation already push new workflows toward Python NNLS:

- `docs/more_info/changelog.rst` says `LegacyWeightSolver` is deprecated and
  will be removed along with GALAHAD in a future DYNAMITE version.
- `dynamite/config_reader.py` rejects `LegacyWeightSolver` for `BayesLOSVD`
  and tells users to use `type: "NNLS"`.

Therefore, legacy Fortran NNLS has not been removed yet, but the active
direction of the project is already Python `NNLS`, especially
`nnls_solver: "scipy"`.

## Benchmark Method

The benchmark used the five completed NGC6278 models from the local audit run
in:

```text
/tmp/dynamite-galahad-run
```

For each model:

1. The old Fortran solver was run in a copied `ml*_bench_matrix_*` directory
   with solver mode `1`.
2. Mode `1` dumped the exact dense NNLS matrix `A`, right-hand side `b`, and
   legacy NNLS solution to `nn_orbmat.out`.
3. Python solvers were run in memory on exactly the same `A, b`.
4. GALAHAD/QPB was run separately in copied `ml*_bench_galahad_*` directories
   with solver mode `5`.

This benchmark measures the weight solve once an orbit library already exists.
It does not include fresh orbit integration time.

Raw benchmark output:

```text
/tmp/dynamite-nnls-benchmark-20260602-001147.json
```

Standalone report:

```text
aidocs/audits/nnls_solver_benchmark_2026-06-01.md
```

Local package versions:

- SciPy `1.17.1`
- NumPy `2.3.5`
- CVXOPT `1.3.3`

CVXOPT was installed only into the repository-local `.venv`.

## Matrix Size and Density

All five benchmark matrices had the same shape:

```text
A = 1121 x 288
```

Rows:

- `513` mass-related constraints
- `608` kinematic constraints

Columns:

- `288` orbit weights

The dumped dense NNLS matrix was about `68.5%` nonzero. This is not sparse
enough to make a sparse solver the obvious first target for this benchmark.

## Timing Summary

Times are wall-clock seconds except where noted.

| Backend | Mean time | Range | Outcome |
| --- | ---: | ---: | --- |
| SciPy `optimize.nnls` | `0.039 s` | `0.029-0.048 s` | matches legacy Fortran NNLS |
| CVXOPT dense QP, refined | `0.120 s` | `0.112-0.130 s` | very close, not exact |
| SciPy `lsq_linear(method="trf")` | `1.741 s` | `1.387-2.166 s` | did not reach same optimum |
| SciPy `lsq_linear(method="bvls")` | `3.232 s` | `1.706-4.301 s` | matches, slower |
| Legacy Fortran NNLS mode 1 | `0.947 s` | `0.917-0.967 s` | matches; includes matrix dump |
| GALAHAD/QPB mode 5 | `10.105 s` | `8.891-14.156 s` | failed, QPB status `-5` |

The legacy Fortran timing includes reading/building the matrix, solving,
writing outputs, and dumping `nn_orbmat.out`. It is not a pure solver-kernel
time. The SciPy/CVXOPT timings are in-memory solves on the already dumped
matrix.

## Numerical Results

SciPy `optimize.nnls` matched the old Fortran Lawson-Hanson NNLS solution to
roundoff:

```text
max absolute weight difference vs legacy Fortran NNLS: <= 6.3e-15
```

SciPy `lsq_linear(method="bvls")` also matched the same optimum, but was much
slower:

```text
max absolute weight difference vs legacy Fortran NNLS: <= 2.1e-12
```

CVXOPT with default settings was mostly close, but one model was noticeably
looser. With stricter tolerances and iterative refinement, all five models were
close:

```text
max absolute weight difference vs SciPy NNLS: <= 6.6e-6
max chi2 increase vs SciPy NNLS: <= 1.4e-4
```

The refined CVXOPT settings used were:

```python
cvxopt.solvers.options["abstol"] = 1e-12
cvxopt.solvers.options["reltol"] = 1e-12
cvxopt.solvers.options["feastol"] = 1e-12
cvxopt.solvers.options["maxiters"] = 500
cvxopt.solvers.options["refinement"] = 3
```

SciPy `lsq_linear(method="trf")` was not equivalent in the tested settings.
It returned success statuses, but the objective was higher by thousands to tens
of thousands in total chi-square.

GALAHAD/QPB mode `5` failed on every tested model:

```text
QPB_solve exit status = -5
```

The shell process still exited successfully, but QPB reported infeasibility or
inconsistent constraints. The resulting weights did not match the valid NNLS
solution and the recomputed total chi-square was enormous. These GALAHAD
outputs should be treated as invalid for this benchmark.

## What The Benchmark Proves

The benchmark proves the following for the tested NGC6278 plain-NNLS problems:

- The Python SciPy backend can reproduce the old Fortran NNLS results.
- The Python SciPy backend is faster than the tested alternatives once the
  matrix already exists.
- GALAHAD/QPB mode `5` is not a valid replacement for plain NNLS in the current
  local state.
- CVXOPT is installable locally and usable as a cross-check, but it is not the
  best default for these dense plain-NNLS problems.

The benchmark does not prove the following:

- It does not prove parity for every galaxy/configuration.
- It does not prove CRcut parity.
- It does not prove barred-model parity.
- It does not prove parity for historical publications without rerunning their
  exact configurations.
- It does not benchmark fresh orbit-library generation, which is dominated by
  Fortran orbit integration and disk I/O rather than the NNLS solve itself.

## Existing Test Assets

The repository already contains useful starting points, but most are
script-style checks rather than strict unit tests.

Relevant existing files:

- `archive/dev_tests/test_reimplement_nnls.py`
  - runs `reimplement_nnls_config1.yaml` with `LegacyWeightSolver`;
  - runs `reimplement_nnls_config2.yaml` with Python `NNLS`;
  - compares one model's weights with `np.allclose`;
  - compares the `kinchi2` grid with `np.allclose`;
  - currently produces plots and text output, but does not fail the process if
    the comparison is bad.
- `archive/dev_tests/test_nnls.py`
  - runs a Python `NNLS/scipy` workflow and compares against stored chi-square
    comparison data visually/textually;
  - useful as a regression-test base, but currently more integration-script
    than pytest.
- `archive/dev_tests/test_all.sh`
  - can sweep `LegacyWeightSolver` and `NNLS/scipy` across generator types;
  - currently checks only exit codes, not scientific parity.
- `archive/dev_tests/test_bar.py` and `archive/dev_tests/bartest.yaml`
  - useful seed for barred-model coverage;
  - current comparison logic is partly commented out.
- `archive/dev_tests/bayes_losvd/IC0719_dynamite_config.yaml`
  - useful seed for the BayesLOSVD path, which already requires Python `NNLS`.

These assets should be converted into deterministic pass/fail tests before
removing old solver code.

## Required Tests Before Replacing Or Removing Legacy Solver Code

If the Fortran NNLS/GALAHAD path is replaced by newer Python code, the minimum
test suite should prove scientific parity at three levels: solver kernel,
matrix construction, and end-to-end model outputs.

### 1. Pure Solver Kernel Tests

Purpose: prove that a Python solver gives the same answer for an already
constructed NNLS problem.

Fixture:

- store a small set of frozen matrices as `.npz` fixtures:
  - `A`;
  - `b`;
  - legacy Fortran NNLS weights;
  - legacy total chi-square;
  - legacy kinematic chi-square;
  - row-block metadata for mass and kinematic rows.

Test cases:

- `scipy.optimize.nnls(A, b)` must match legacy Fortran weights to strict
  tolerance.
- recomputed total chi-square must match legacy chi-square.
- recomputed kinematic chi-square must match legacy kinematic chi-square.
- weights must be finite and non-negative.
- output shape must equal the number of orbit columns.

Recommended tolerances based on the benchmark:

```text
weights: rtol=1e-10, atol=1e-10 for SciPy NNLS fixture tests
chi2:    rtol=1e-10, atol=1e-6
```

For CVXOPT, the tolerance should be looser unless stricter options are
standardized:

```text
weights: rtol=1e-7, atol=1e-6
chi2:    rtol=1e-9, atol=1e-3
```

CVXOPT should be marked optional, because it is not part of the standard
install path.

### 2. Matrix-Construction Parity Tests

Purpose: prove that the Python path constructs the same scientific problem the
legacy route solved.

Start from:

- `archive/dev_tests/reimplement_nnls_config1.yaml`
- `archive/dev_tests/reimplement_nnls_config2.yaml`
- `archive/dev_tests/test_reimplement_nnls.py`

Convert the current script into a pytest-style test that:

1. runs the legacy config in a temporary output directory;
2. reuses the generated orbit library;
3. runs the Python `NNLS/scipy` config in a temporary output directory;
4. compares all models, not just model 0;
5. fails on mismatch instead of only writing a plot.

Required comparisons:

- weights for every model;
- `chi2`;
- `kinchi2`;
- `kinmapchi2`;
- model table row count and parameter values;
- all finite/non-negative weight arrays;
- no silent solver failures in logs or status metadata.

This test should use temporary directories and should not delete or mutate
checked-in dev-test outputs.

### 3. End-To-End Regression Tests

Purpose: prove that replacing the solver does not change the model-selection
result a user sees.

Recommended fixtures:

- one small Gauss-Hermite triaxial model;
- one M/L sweep where one orbit library is reused across several `ml` values;
- one `CRcut: True` case;
- one barred-model case;
- one BayesLOSVD case, Python `NNLS` only.

Required comparisons:

- best model id under configured `which_chi2`;
- sorted `chi2`, `kinchi2`, and `kinmapchi2` arrays;
- generated weights files and metadata;
- model completion flags: `orblib_done`, `weights_done`, `all_done`;
- no NaN weights or chi-square values unless the test intentionally exercises a
  failure case.

These should be marked as slower integration tests, separate from pure unit
tests.

### 4. Failure-Mode Tests

Purpose: avoid repeating the GALAHAD/QPB issue where a solver can fail
internally but downstream code still sees output files.

Test cases:

- corrupted or missing solver output must fail explicitly;
- non-zero Fortran subprocess return code must fail explicitly;
- GALAHAD/QPB non-success status must fail explicitly;
- all-NaN, negative, wrong-length, or non-finite weights must fail explicitly;
- missing `nn_orbmat.out`, `nn_kinem.out`, or weight ECSV metadata must fail
  explicitly for the legacy route.

These tests should be required before keeping legacy/GALAHAD as a supported
backend.

### 5. Performance Guardrail Tests

Purpose: prevent accidental solver regressions without making CI flaky.

The benchmark found SciPy NNLS around `0.03-0.05 s` on a `1121 x 288` matrix in
this local environment. CI should not require an exact runtime. Instead:

- keep a benchmark script outside the normal fast unit suite;
- record matrix shape, density, backend, package versions, and wall time;
- fail only on severe regressions, for example a 10x slowdown on the same
  frozen fixture.

This is a guardrail, not the main correctness test.

## Suggested Pytest Structure

A clean future layout could be:

```text
tests/
  fixtures/
    nnls_ngc6278_model0.npz
    nnls_ngc6278_model1.npz
  test_nnls_solver_kernel.py
  test_nnls_legacy_parity.py
  test_nnls_failure_modes.py
  test_solver_config_dispatch.py
  test_bayes_losvd_solver_requirements.py
```

Suggested markers:

```text
@pytest.mark.slow
@pytest.mark.legacy_fortran
@pytest.mark.galahad
@pytest.mark.cvxopt
```

The fast default suite should always run pure Python solver-kernel and config
dispatch tests. Slow legacy/GALAHAD tests can run in nightly or manual audit
runs when the local Fortran binaries are available.

## Removal Gate

The old Fortran NNLS and GALAHAD path should not be deleted just because one
benchmark looked good. Deletion should require a clear gate:

1. pure solver fixture tests pass for SciPy NNLS;
2. `test_reimplement_nnls.py` is converted to a real pass/fail parity test;
3. parity passes for all models in the legacy-vs-Python reimplementation
   configs;
4. at least one CRcut fixture is covered;
5. at least one M/L reuse fixture is covered;
6. barred-model behavior is either covered or explicitly declared out of scope;
7. BayesLOSVD remains covered on the Python `NNLS` path;
8. legacy/GALAHAD failure statuses are no longer silently accepted;
9. Thomas confirms whether historical reproduction of old published models is
   still required.

Only after this gate passes should removal be considered scientifically safe.

## Practical Removal Options

Thomas has three realistic options.

### Option A - Remove GALAHAD From The Required Workflow Now

This is the lowest-risk simplification.

Keep:

- Python `NNLS` with `nnls_solver: "scipy"`;
- optional CVXOPT backend;
- possibly old Fortran source for historical reference.

Remove from the required install path:

- GALAHAD setup;
- GALAHAD environment variables;
- expectation that users must build the full `triaxnnls_*` GALAHAD-linked
  binaries.

Pros:

- simpler installation;
- fewer old vendored numerical dependencies;
- avoids the observed QPB failure-status problem;
- consistent with existing documentation that Python-only installation is
  supported.

Cons:

- old configs using `LegacyWeightSolver` need migration;
- users reproducing old legacy runs may still need the old path;
- constrained GALAHAD modes would no longer be available unless replaced.

This option is supported by the benchmark.

### Option B - Deprecate LegacyWeightSolver Hard, Then Remove It After Parity Tests

This is the safest scientific path.

Keep legacy Fortran/GALAHAD temporarily as a compatibility backend, but stop
treating it as normal infrastructure. Add a parity harness first:

- archived `LegacyWeightSolver` behavior vs Python `NNLS/scipy`;
- CRcut true/false;
- multiple M/L values sharing one orbit library;
- barred models;
- representative Gauss-Hermite configs;
- BayesLOSVD remains Python `NNLS` only;
- validation that all weights are finite, non-negative, and shape-correct.

Pros:

- preserves reproducibility during transition;
- gives a defensible scientific removal path;
- can detect hidden differences outside the five benchmark models.

Cons:

- more work before deletion;
- keeps old dependencies around longer;
- does not immediately simplify the repository as much as option A.

This was the recommended transition route. The local branch has taken the
stronger cleanup step: `LegacyWeightSolver` is rejected and the old sources are
archived.

### Option C - Keep GALAHAD And Legacy Fortran Indefinitely

This is the conservative historical-compatibility option.

Pros:

- old configurations remain directly runnable;
- GALAHAD modes remain available for investigation;
- useful for regression comparison.

Cons:

- install remains fragile;
- old vendored dependency stack remains a maintenance burden;
- GALAHAD/QPB mode `5` failed in this audit;
- users may assume GALAHAD is required even when SciPy NNLS is better for
  plain NNLS.

This option is not attractive for new development.

## Recommendation

Current local recommendation: keep GALAHAD removed from the
required/recommended workflow and keep the old solver code archived unless a
specific reproduction task requires a controlled restore.

Recommended staged decision:

1. Make Python `NNLS` with `nnls_solver: "scipy"` the only recommended path for
   new plain-NNLS work.
2. Reject `LegacyWeightSolver` in active configuration/model execution.
3. Stop requiring GALAHAD in local setup and CI.
4. Add a small parity harness that compares old Fortran NNLS and Python SciPy
   NNLS on representative fixtures.
5. Keep `LegacyWeightSolver` and the GALAHAD-linked Fortran solver build out of
   the active code path.
6. Keep archived legacy source or a tagged branch if old result reproduction is
   still needed.

For Thomas's decision: the benchmark gives strong evidence that GALAHAD should
not be kept as a required dependency for normal plain-NNLS DYNAMITE work. The
only strong argument for keeping it is historical compatibility or if the
constrained GALAHAD modes are scientifically required and then fixed.

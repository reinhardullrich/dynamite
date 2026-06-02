# 15 Active NNLS Solver Policy And Benchmark Plan

Date: 2026-06-02

Scope: current active Python weight solving only. This chapter covers only the
active Python `NNLS` path and its validation, caching, tests, and benchmark
policy.

## Executive Conclusion

The active weight-solver path for this local branch is Python `NNLS`.

Recommended active configuration:

```yaml
weight_solver_settings:
    type: "NNLS"
    nnls_solver: "scipy"
```

The SciPy backend should remain the default active plain-NNLS backend unless a
new current-code benchmark shows a better choice. CVXOPT remains an optional
cross-check backend, not the default.

The important engineering work is not to add more solver choices first. It is
to make the active solver problem explicit, validated, cached, and benchmarked
with deterministic fixtures.

## Active Solver Entry Point

The active solver path is in `dynamite/weight_solvers.py`:

- `NNLS` builds the weight-solving matrix and right-hand side from the current
  model's orbit library, mass constraints, projected mass constraints, and
  kinematic constraints.
- `nnls_solver: "scipy"` calls SciPy's non-negative least-squares solver.
- `nnls_solver: "cvxopt"` solves an equivalent non-negative quadratic problem
  when CVXOPT is installed.

The solver input is conceptually:

```text
minimize ||A x - b||^2
subject to x >= 0
```

where:

- `A` is the assembled model matrix;
- `b` is the assembled target vector;
- `x` is the non-negative orbit-weight vector.

## Active Benchmark Interpretation

The current practical policy is:

- use SciPy for normal plain-NNLS work;
- use CVXOPT only when an explicit cross-check is needed;
- benchmark matrix construction separately from the numerical solve;
- report matrix shape, density, scaling, backend, elapsed time, and status;
- validate output arrays before writing or accepting model results.

A useful benchmark for the active code must split time into:

1. orbit-library readback;
2. matrix/RHS assembly;
3. backend solve;
4. chi-square reconstruction;
5. weight/output writing.

Without that split, a faster numerical solve can be hidden by matrix assembly or
disk I/O.

## Required Solver Validation

Every active solver run should validate:

- `A` and `b` are finite;
- matrix dimensions match the expected number of constraints and orbit columns;
- row scaling is finite and non-zero where required;
- returned weights are finite;
- returned weights are non-negative within a documented tolerance;
- chi-square values are finite;
- output shapes match the orbit-library reader expectations;
- backend status and elapsed time are recorded.

Validation should happen before model status is marked complete.

## Proposed `SolverProblem`

The active code should expose an internal `SolverProblem` object before adding
new solver behavior:

```python
SolverProblem(
    matrix=A,
    rhs=b,
    row_metadata=row_metadata,
    orbit_metadata=orbit_metadata,
    scaling=scaling,
    settings_hash=settings_hash,
    source_hashes=source_hashes,
)
```

The object should be serializable to a binary fixture for tests and benchmarks.

Minimum metadata:

- model key;
- orbit-library key;
- solver settings hash;
- kinematic input hashes;
- mass-constraint settings;
- matrix shape;
- matrix density;
- velocity scaling;
- units and row-block labels.

## Proposed `SolverResult`

The active code should return an internal `SolverResult` object:

```python
SolverResult(
    weights=weights,
    chi2_total=chi2_total,
    chi2_kinematic=chi2_kinematic,
    chi2_kinematic_maps=chi2_kinematic_maps,
    backend="scipy",
    status="success",
    diagnostics=diagnostics,
)
```

Minimum diagnostics:

- elapsed solver time;
- iteration or backend status if available;
- matrix shape and density;
- max negative weight before tolerance clipping, if any;
- residual norm;
- finite/non-negative validation result.

## Active Test Plan

### Solver Kernel Fixtures

Create small `.npz` fixtures containing:

- `A`;
- `b`;
- expected SciPy weights;
- expected total chi-square;
- row-block metadata.

Assertions:

- weights match fixture values to strict tolerance;
- chi-square reconstruction matches fixture values;
- weights are finite and non-negative;
- matrix and RHS shapes are exact.

Suggested tolerance for deterministic fixture comparisons:

```text
weights: rtol=1e-12, atol=1e-12 where stable
chi2:    rtol=1e-12, atol=1e-10 where stable
```

If platform-level BLAS or solver details create tiny differences, document the
observed bound and keep it separate from scientific output tolerances.

### Matrix Construction Fixtures

Create fixtures that build `SolverProblem` from a small active orbit-library
fixture and assert:

- row-block counts;
- matrix shape;
- RHS shape;
- finite values;
- density bounds;
- source hashes;
- stable solver key.

### End-To-End Weight Fixtures

For a small model fixture:

- generate or reuse the active orbit-library fixture;
- build `SolverProblem`;
- solve with SciPy;
- write weights;
- read weights back;
- assert model chi-square fields and status values.

These tests should run in temporary output directories and must not mutate
checked-in fixtures except when explicitly regenerating them.

## Cache Policy

Prepared solver data may be cached only when every relevant dependency is part
of the key:

- orbit-library key;
- kinematic input hashes;
- solver settings;
- row scaling settings;
- velocity scaling;
- code/schema version.

Cache mismatch must be a hard miss or a clear error. Do not silently reuse a
nearby matrix.

## Benchmark Output Format

A useful active benchmark report should include:

```text
model_key:
orblib_key:
solver_key:
backend:
matrix_shape:
matrix_density:
assembly_seconds:
solve_seconds:
write_seconds:
chi2_total:
chi2_kinematic:
weights_min:
weights_max:
weights_nonzero:
status:
```

This gives enough information to decide whether the next performance task is
matrix assembly, solving, I/O, or orbit-library generation.

## Recommendations

1. Keep `type: "NNLS"` with `nnls_solver: "scipy"` as the active default.
2. Add `SolverProblem` and `SolverResult` internally.
3. Add deterministic solver-kernel fixtures.
4. Add matrix-construction fixtures from active orbit-library data.
5. Record solver benchmark manifests for representative model runs.
6. Cache prepared matrix blocks only after strict keying and fixture coverage
   are in place.
7. Keep CVXOPT as an optional cross-check backend unless active benchmarks show
   a clear reason to promote it.

# 15 Active NNLS Solver Policy And Benchmark Plan

Audit date: 2026-06-04

## Executive Conclusion

The active solver path is Python `NNLS` with SciPy as the recommended default
for plain dense non-negative least squares.

## Current Active Entry Point

- `dynamite/model.py`: `Model.get_weights()` selects `ws.NNLS`.
- `dynamite/weight_solvers.py`: `NNLS.solve()` constructs the matrix/rhs,
  solves with SciPy or CVXOPT, computes chi-square, and writes weights.

Recommended active config:

```yaml
weight_solver_settings:
  type: "NNLS"
  nnls_solver: "scipy"
```

## Current Solver Options

### SciPy `optimize.nnls`

Pros:

- simple dependency already in runtime stack;
- direct solver for the active problem form;
- already used by the current active configuration path.

Cons:

- no rich status object in current DYNAMITE wrapper;
- current wrapper needs stronger finite/non-negative/shape validation.

### CVXOPT

Pros:

- solves a quadratic-program form;
- exposes solver status internally.

Cons:

- optional dependency;
- current wrapper computes `success` but does not enforce it in `NNLS.solve()`;
- likely not the first choice for the plain NNLS path unless benchmarks justify
  it.

## Required Before More Solver Benchmarking

Add `SolverProblem`:

- matrix `A`;
- rhs `b`;
- orbit-library key;
- model key;
- kinematic/mass constraint metadata;
- scaling/error metadata;
- source hashes.

Add `SolverResult`:

- backend name;
- backend status;
- success/failure;
- weights;
- residual norm;
- chi-square components;
- finite/non-negative checks;
- shape checks;
- timing split.

## Benchmark Plan

For each representative model:

1. Time orbit-library read/load.
2. Time intrinsic/projected mass and LOSVD preparation.
3. Time matrix/rhs construction.
4. Record matrix shape, dtype, density, memory footprint.
5. Time SciPy solve.
6. Time CVXOPT solve if installed and feasible.
7. Compare weights, residual norm, chi-square, and active constraints.
8. Time result writing.

## Acceptance Rules

- Do not accept a faster solver if weights or chi-square diverge beyond
  explicit scientific tolerance.
- Treat non-finite weights, negative weights, failed backend status, or
  non-finite chi-square as failure.
- Benchmark on current generated orbit-library fixtures and at least one
  larger representative real model before changing defaults.

## Current Recommendation

Keep `NNLS` + `scipy` as the active default. Improve validation and timing
first; benchmark alternative solvers after the input/result contracts exist.

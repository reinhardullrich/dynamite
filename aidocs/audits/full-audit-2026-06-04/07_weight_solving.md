# 07 Weight Solving

Audit date: 2026-06-04

## Scope

Active Python NNLS, optional CVXOPT backend, matrix construction, solver
validation, and output writing.

## Current State

The active runtime uses `type: NNLS` and `nnls_solver: scipy` by default.

## Findings

### WS-001 - Active Python NNLS lacks explicit solver-result contract

Severity: High.

Evidence:

- `NNLS.solve()` catches solver exceptions and fills all weights with NaN.
- successful solve handling checks only `np.isnan(weights[0])`.
- there is no common object recording backend status, iterations, residual
  norm, finite/non-negative checks, matrix/rhs dimensions, and chi-square
  diagnostics.

Recommendation: introduce `SolverProblem` and `SolverResult` and make failure
states hard errors unless the caller explicitly requests a nonfatal result.

### WS-002 - CVXOPT success is computed but not enforced

Severity: Medium.

Evidence:

- `CvxoptNonNegSolver.success` is set from `sol['status'] == 'optimal'`.
- `NNLS.solve()` uses `solver.beta` but does not check `solver.success`.

Recommendation: fail if CVXOPT status is not optimal; record status in
`SolverResult`.

### WS-003 - NNLS matrix construction has no prepared-input cache

Severity: Medium/Performance.

Matrix construction scales with orbit count, constraints, kinematic sets, and
intrinsic qgrid size. Repeated solves for the same orbit library/settings can
rebuild identical matrix blocks.

Recommendation: cache prepared matrix blocks only after stable `orblib_key`,
settings hash, and input-data hashes exist.

### WS-004 - Weight output writes are direct

Severity: Medium.

Evidence:

- `NNLS.solve()` writes `self.weight_file` directly with `overwrite=True`.

Recommendation: write to a temporary file, validate readback/meta, then
`os.replace()`.

### WS-005 - Active tests cover important but not complete solver behavior

Severity: Medium.

- full matrix construction fixtures;
- non-finite/negative output rejection;
- CVXOPT status handling;
- large model timing split between matrix construction and solve.

Recommendation: add solver-kernel, matrix-construction, and end-to-end
weight-output fixtures before changing active solver internals.

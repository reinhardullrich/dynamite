# NNLS Solver Benchmark

Scope: local dense NNLS/QP benchmark on the existing NGC6278 audit run in
`/tmp/dynamite-galahad-run`.

Raw benchmark output:

- `/tmp/dynamite-nnls-benchmark-20260602-001147.json`

Local package versions:

- SciPy `1.17.1`
- NumPy `2.3.5`
- CVXOPT `1.3.3`

CVXOPT was installed only into the repository-local `.venv`.

## Method

The benchmark used the five completed NGC6278 legacy models from the local
audit run. For each model, the legacy Fortran solver was run in a copied
`ml*_bench_matrix_*` directory with solver mode `1`, which dumps the exact
dense NNLS matrix `A`, right-hand side `b`, and legacy NNLS solution to
`nn_orbmat.out`.

The Python/CVXOPT solvers were then run on exactly that same `A, b` pair.
GALAHAD/QPB was run separately in copied `ml*_bench_galahad_*` directories
with solver mode `5`.

This benchmark measures weight-solving behavior after an orbit library already
exists. It does not include orbit integration time.

## Matrix Size

All five benchmark matrices had the same shape:

```text
A = 1121 x 288
```

Rows:

- `513` mass-related constraints
- `608` kinematic constraints

Columns:

- `288` orbit weights

The dumped dense NNLS matrix was about `68.5%` nonzero. In the GALAHAD/QPB
formulation, the constrained submatrix printed about `48%` nonzero, while the
Hessian was effectively dense.

## Timing Summary

Times are wall-clock seconds except where noted.

| Backend | Mean time | Range | Outcome |
| --- | ---: | ---: | --- |
| SciPy `optimize.nnls` | `0.039 s` | `0.029-0.048 s` | matches legacy NNLS |
| CVXOPT dense QP, refined | `0.120 s` | `0.112-0.130 s` | very close, not exact |
| SciPy `lsq_linear(method="trf")` | `1.741 s` | `1.387-2.166 s` | did not reach same optimum |
| SciPy `lsq_linear(method="bvls")` | `3.232 s` | `1.706-4.301 s` | matches, slower |
| Legacy Fortran NNLS mode 1 | `0.947 s` | `0.917-0.967 s` | matches; includes matrix dump |
| GALAHAD/QPB mode 5 | `10.105 s` | `8.891-14.156 s` | failed, QPB status `-5` |

The legacy Fortran timing includes reading/building the matrix, solving, writing
outputs, and dumping `nn_orbmat.out`; it is not a pure solver-kernel time.

## Numerical Outcome

SciPy `optimize.nnls` matched the legacy Fortran NNLS solution to roundoff:

```text
max absolute weight difference vs legacy NNLS: <= 6.3e-15
```

SciPy `lsq_linear(method="bvls")` also matched the same optimum, but was much
slower:

```text
max absolute weight difference vs legacy NNLS: <= 2.1e-12
```

CVXOPT with default settings was mostly close but had one noticeably looser
case. With stricter tolerances and `refinement=3`, all five models were close:

```text
max absolute weight difference vs SciPy NNLS: <= 6.6e-6
max chi2 increase vs SciPy NNLS: <= 1.4e-4
```

SciPy `lsq_linear(method="trf")` was not equivalent with the tested settings.
It returned success statuses, but the objective was higher by thousands to tens
of thousands in total chi-square.

GALAHAD/QPB mode `5` failed on every tested model:

```text
QPB_solve exit status = -5
```

The shell process still exited successfully, but QPB reported infeasibility or
inconsistent constraints. The resulting weights did not match the valid NNLS
solution and the recomputed total chi-square was enormous, so these GALAHAD
outputs should be treated as invalid.

## Conclusion

For the dense NNLS problem as currently used by DYNAMITE, SciPy
`optimize.nnls` is the best default backend:

- fastest valid backend in this benchmark;
- exact parity with legacy Fortran NNLS on all five tested models;
- already part of the project dependencies;
- avoids GALAHAD/HSL installation and runtime-status problems.

CVXOPT is feasible as an optional cross-check backend, but it should not be the
preferred default. It solves the normal-equation QP and needs stricter settings
to match well:

```python
cvxopt.solvers.options["abstol"] = 1e-12
cvxopt.solvers.options["reltol"] = 1e-12
cvxopt.solvers.options["feastol"] = 1e-12
cvxopt.solvers.options["refinement"] = 3
```

GALAHAD/QPB mode `5` is not a viable replacement path in the current local
state. It is slower than SciPy NNLS on this benchmark and did not produce valid
solutions.

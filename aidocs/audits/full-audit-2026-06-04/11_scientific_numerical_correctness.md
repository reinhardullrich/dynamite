# 11 Scientific and Numerical Correctness Audit

Audit date: 2026-06-04

## Overall Assessment

The largest correctness risks are acceptance criteria, domain validation,
atomic state, solver contracts, and missing rotating-frame fixtures.

## Findings

### SNC-001 - Solver output is not yet a validated scientific result object

Severity: High.

Active NNLS should return an explicit result object with backend status,
finite/non-negative checks, residuals, chi-square components, matrix/rhs shape,
and input hashes.

Current code computes and writes weights/chi-square but lacks that full
acceptance object.

### SNC-002 - Physical parameter domains are incompletely enforced

Severity: High.

Logarithmic transforms, halo parameters, viewing parameters, and data arrays
need centralized finite/domain validation before reaching Fortran or solver
code.

### SNC-003 - Rotating-frame scientific parity is not covered

Severity: High for `Omega != 0` work.

PF-01/PF-02/PF-03 preserved rotating-frame structure carefully, but the test
fixture is non-rotating. There is no real generated-output fixture for
`Omega != 0`.

Recommendation: add a minimal rotating-frame fixture before further work on bar
or sign/symmetry logic.

### SNC-004 - Numerical integration diagnostics are not model-quality metadata

Severity: Medium.

Integration/interpolation diagnostics are printed/logged but not stored as
structured metadata used in model acceptance.

Recommendation: add per-model diagnostic manifests with warning counts,
interpolation misses, orbit failures, and timing.

### SNC-005 - Model/orbit-library reuse can conflate close parameter rows

Severity: Medium/High.

Tolerance-based `np.allclose()` matching remains common. Scientific model
identity should be explicit and reproducible.

Recommendation: add `model_key` and `orblib_key`.

### SNC-006 - Unit conversion and output-format contracts need more focused tests

Severity: Medium.

Current tests cover LOSVD/qgrid/orbclass for one fixture. More tests are needed
for unit conversions, multiple kinematic sets, populations, BayesLOSVD, and
rotating/barred systems if those remain supported.

### SNC-007 - Non-atomic writes can create scientifically ambiguous output state

Severity: High.

Interrupted writes can leave model tables, weights, caches, or orbit-library
outputs inconsistent with done markers or metadata.

Recommendation: atomic writes and output manifests should be treated as
scientific correctness work, not just operational cleanup.

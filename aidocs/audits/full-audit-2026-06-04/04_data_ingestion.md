# 04 Data Ingestion

Audit date: 2026-06-04

## Scope

MGE tables, kinematic inputs, population inputs, aperture/bin files, BayesLOSVD
conversion, and data-preparation boundaries.

## Findings

### DI-001 - Finite-value validation is uneven at data boundaries

Severity: Medium/High.

Many readers and transformations rely on downstream NumPy/Astropy failures or
partial checks instead of central finite-value validation for every numeric
column used by the runtime.

Recommendation: validate required columns, shapes, units, finite values, and
non-negative uncertainties when each external table/file is loaded.

### DI-002 - Kinematic velocity-grid checks still use `assert`

Severity: Medium.

Evidence:

- kinematic histogram paths use `assert np.allclose(...)` for uniform velocity
  bin checks.

Impact: optimized Python can disable these checks.

Recommendation: replace scientific/data-boundary asserts with explicit hard
errors.

### DI-003 - BayesLOSVD conversion handles missing bins but still needs stronger contracts

Severity: Medium.

BayesLOSVD mapping code accounts for missing bins, but the interface needs
stronger validation around required columns, completed-bin ordering, histogram
metadata, and finite values.

Recommendation: add small BayesLOSVD fixture tests covering missing bins,
wrong metadata, non-finite entries, and mismatched aperture/bin files.

### DI-004 - Aperture/bin file parsing remains a critical Fortran/Python contract

Severity: Medium.

The direct shared-library API reads aperture and binning data in Python and
passes arrays to Fortran. The aperture/bin file formats remain scientific
contracts.

Recommendation: keep fixture tests for aperture geometry, bin ordering, PSF
assignment, and histogram dimensions.

### DI-005 - Data-prep workflows remain under-tested in active pytest

Severity: Medium.

The active pytest suite has strong fixture coverage for selected examples and
orblib paths, but data-prep workflows are not fully represented as current
tests.

Recommendation: add focused tests for data-prep outputs if those workflows are
expected to stay supported.

# 08 Fortran Backend Audit

Audit date: 2026-06-04

## Current Active Backend

Active source lives under `orblib_fortran/source/`. The supported local build
product is:

```text
orblib_fortran/build/lib/liborblib_fortran.so
```

## Findings

### FB-001 - Active Fortran build flags reduce portability/reproducibility

Severity: Medium.

Evidence:

- `orblib_fortran/makefile` and `makefile.linux` use `-ffast-math -O3
  -march=native`.

Recommendation: add documented build profiles and use parity tests as the
acceptance gate for `native-fast`.

### FB-002 - Fatal Fortran errors are not fully structured

Severity: Medium.

- Fortran internal failures can still be `stop`/print/log in some lower-level
  routines;
- generated binary output is not accompanied by a full manifest.

Recommendation: keep moving fatal Fortran errors toward explicit status returns
or structured failure records.

### FB-003 - Integration warnings are not model-quality metadata

Severity: Medium.

Integration diagnostics are printed/logged but not propagated into a structured
model-quality record.

Recommendation: write per-model/orbit-library diagnostic metadata: integration
warnings, interpolation misses, rejected orbits, and timing breakdown.

### FB-004 - Rotating-frame Fortran behavior lacks a dedicated fixture

Severity: Scientific sensitivity medium.

There is no dedicated real rotating-frame `Omega != 0` fixture for the active
Fortran shared-library path.

Recommendation: add that fixture before additional rotating/symmetry refactors.

### FB-005 - Dense qgrid output remains large

Severity: Medium/Performance.

The qgrid file still writes dense 16-channel arrays. PF-02 reduced hot-path
computation but did not change output format or size.

Recommendation: measure nonzero qgrid occupancy before designing sparse or
density-only output formats.

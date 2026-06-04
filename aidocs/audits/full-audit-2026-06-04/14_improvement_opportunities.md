# 14 Improvement Opportunities

Audit date: 2026-06-04

This chapter intentionally focuses on future improvements, not bug fixes.

## Current Active Runtime

The active non-bar runtime spends its meaningful model-generation time in the
Fortran shared-library orbit-library path and surrounding disk I/O. Python
startup/import time matters for short developer workflows and tests, but not
for full production orbit integrations that can run for days/weeks.

## Highest-Payoff Improvements

### IM-001 - Add per-stage timing manifests

Payoff: high for performance work.

Add structured timing for:

- orbit-start generation;
- tube orbit generation;
- box orbit generation;
- DOP853 integration;
- qgrid store/write;
- projection/PSF/aperture/histogram;
- output compression/readback;
- NNLS matrix construction;
- NNLS solve;
- table/cache writes.

### IM-002 - Add output manifests and binary contract versioning

Payoff: high for correctness and future format changes.

Each model/orbit-library run should write a manifest with ABI version, build
profile, input hashes, output filenames, sizes, hashes, timings, and warning
counts.

### IM-003 - Cache prepared NNLS matrix blocks

Payoff: medium/high for repeated solves.

Do this only after stable `orblib_key`, settings hashes, and data hashes exist.

### IM-004 - Introduce `SolverProblem` and `SolverResult`

Payoff: high for maintainability and scientific acceptance.

This should come before experimenting with more solver backends.

### IM-005 - Add stable model and orbit-library keys

Payoff: high.

Replaces repeated `np.allclose()` table scans and clarifies reuse semantics.

### IM-006 - Make writes atomic

Payoff: high for long runs.

Use temp files plus `os.replace()` for ECSV, NPZ, YAML, weight files, and
runtime metadata.

### IM-007 - Add rotating-frame regression fixture

Payoff: high for safe Fortran cleanup.

Needed before treating `Omega != 0` refactors as scientifically verified.

### IM-008 - Build profiles

Payoff: medium.

Add `debug`, `portable-release`, and `native-fast` Fortran build profiles.

### IM-009 - Lighter imports

Payoff: low/medium.

Useful for developer ergonomics and pytest collection. Full production model
runs remain dominated by Fortran orbit generation.

## What Not To Do First

- Do not change qgrid/LOSVD binary formats before adding manifests and
  readback tests.
- Do not add new NNLS solvers before result validation is explicit.
- Do not optimize import time before timing manifests show it matters for the
  workflow being optimized.
- Do not refactor rotating-frame symmetry further before adding a real
  rotating fixture.

# 14 Improvement Opportunities

Date: 2026-06-02

Scope: non-bug-fix improvements for the current active DYNAMITE code paths. It
covers the active Python package, the direct orblib shared-library backend, the
active Python `NNLS` solver path, current binary `datfil/` outputs, and the
current pytest baseline under `tests/`.

## Current Active Runtime

The active runtime shape is:

1. Python configuration and model iteration in `dynamite/`.
2. Orbit-library generation through `dynamite/orblib_api.py`.
3. Shared-library calls into
   `orblib_fortran/build/lib/liborblib_fortran.so`.
4. Binary orbit-library outputs under model `datfil/` directories.
5. Readback through the existing Python orbit-library readers.
6. Weight solving through Python `NNLS`.
7. Model bookkeeping in `all_models.ecsv` and generated output folders.

The highest-payoff improvements are therefore around observability, cache
correctness, data formats, solver-matrix reuse, build profiles, and clear
runtime contracts. None of these require changing the scientific model first.

## Guiding Principle

Do not optimize by rewriting the scientific core blindly. First make runtime
behavior measurable and reproducible:

- record wall time by stage;
- record bytes read and written by stage;
- record shared-library ABI version and build flags;
- record process count, CPU count, and random seed;
- record orbit-library cache hits and misses;
- record solver backend, matrix shape, and matrix density;
- record output schema versions for generated binary/cache files.

After that, improve the boundaries where the active code already spends time:
imports, disk I/O, decompression, matrix assembly, repeated model lookup, and
shared-library orchestration.

## Highest-Payoff Improvements

### IM-001 - Add Per-Stage Timing Manifests

Potential payoff: immediate visibility into where time is spent.

Current problem:

- model generation, orbit-start generation, tube/box integration, LOSVD
  readback, solver-matrix assembly, solving, and output writing are not recorded
  in one structured timing artifact;
- performance conclusions are easy to confuse because orbit generation, disk
  I/O, and solver setup have very different cost profiles.

Improvement:

Write a small per-model timing manifest with:

- stage name;
- start/end timestamps;
- elapsed wall time;
- process id;
- input/output paths touched;
- output byte counts when cheap to measure;
- shared-library ABI version for orblib stages;
- solver matrix dimensions for weight stages.

Implementation size: small/medium.

Risk: low if timing writes are append-safe and do not affect scientific output.

### IM-002 - Replace Hot-Path Text Storage With Binary Sidecars

Potential payoff: faster repeated reads and lower parsing overhead.

Current problem:

- `all_models.ecsv`, weights, mass arrays, and derived analysis tables are
  useful for human inspection but expensive as hot runtime storage;
- repeated runs can spend unnecessary time parsing large ASCII/ECSV artifacts.

Improvement:

Keep ECSV as the inspection/export format, but add binary sidecars for large
runtime arrays:

- `.npz` or HDF5 for dense mass arrays, weights, solver matrices, and derived
  analysis arrays;
- a manifest with schema version, units, source config hash, shapes, and source
  file hashes;
- hard errors on cache/schema mismatch rather than silent fallback.

Implementation size: medium.

Risk: medium. Cache invalidation and schema versioning must be explicit.

### IM-003 - Cache Prepared NNLS Matrix Blocks

Potential payoff: much faster repeated solves when the same orbit library and
observational inputs are reused.

Current problem:

- Python `NNLS` assembles matrix and right-hand-side data for each solve;
- some model grids reuse an orbit library across multiple mass-to-light values
  or solver settings;
- repeated matrix assembly can dominate the weight-solver stage once the orbit
  library already exists.

Improvement:

Introduce a `SolverProblem` cache keyed by:

- orbit-library directory and output schema version;
- kinematic input hashes;
- mass-constraint settings;
- LOSVD/Gauss-Hermite settings;
- velocity scaling and mass-to-light value;
- solver-relevant configuration;
- code/cache schema version.

Cache blocks separately where possible:

- intrinsic mass constraints;
- projected mass constraints;
- kinematic transform blocks;
- final scaled matrix and RHS.

Implementation size: medium.

Risk: medium. Incorrect reuse is worse than recomputation, so cache keys must be
strict.

### IM-004 - Introduce Explicit `SolverProblem` And `SolverResult` Objects

Potential payoff: clearer solver validation, easier caching, cleaner tests.

Current problem:

- matrix construction, backend call, validation, and file writing are tightly
  coupled;
- solver status and output validation are not represented as one structured
  result object.

Improvement:

Use internal typed objects:

```python
SolverProblem(
    matrix=A,
    rhs=b,
    row_metadata=rows,
    column_metadata=orbits,
    scaling=scaling,
    settings_hash=settings_hash,
)

SolverResult(
    weights=weights,
    chi2_total=chi2_total,
    chi2_kinematic=chi2_kinematic,
    status=status,
    backend=backend,
    diagnostics=diagnostics,
)
```

Validation should require:

- finite matrix and RHS;
- expected matrix shape;
- finite weights;
- non-negative weights within documented tolerance;
- finite chi-square values;
- explicit backend status.

Implementation size: medium.

Risk: low/medium if introduced internally before changing public config.

### IM-005 - Add Stable Model And Orbit-Library Keys

Potential payoff: faster lookup and fewer accidental cache collisions.

Current problem:

- model and orbit-library reuse is mostly driven by table scans and directory
  state;
- equality of relevant model parameters is implicit.

Improvement:

Add stable keys next to the existing table data:

- `model_key`: exact parameter-set identity;
- `orblib_key`: parameters that affect orbit-library generation;
- `solver_key`: parameters and settings that affect weight solving.

Keep the current table format, but use these keys for lookup and cache naming.

Implementation size: medium.

Risk: medium. Key definitions must match actual runtime dependencies.

### IM-006 - Harden The Direct Orblib API Boundary

Potential payoff: safer shared-library calls and easier debugging.

Current problem:

- Python passes direct arrays/scalars into Fortran and still consumes binary
  output files;
- worker-process failure is safer than in-process failure, but the result
  contract can become clearer.

Improvement:

Extend the Python-facing orblib request/result layer with:

- explicit ABI version check in every call path;
- input shape summaries in logs/manifests;
- generated output file manifest;
- structured worker-process status;
- required-output validation immediately after tube/box completion;
- deterministic random-seed recording.

Implementation size: small/medium.

Risk: low if validation is added after existing outputs are generated.

### IM-007 - Version The Binary Orbit-Library Output Contract

Potential payoff: safer future output changes.

Current problem:

- binary `datfil/` outputs remain the active interface for readers and solvers;
- changing output layout would require coordinated reader changes.

Improvement:

Add a sidecar manifest per generated orbit library:

- schema version;
- file list;
- expected dimensions;
- byte sizes;
- checksum or fast hash;
- velocity grid metadata;
- shared-library ABI version;
- model/orblib key.

Do not change binary payload layout until the manifest exists and tests cover
the current layout.

Implementation size: medium.

Risk: low for manifest-only work.

### IM-008 - Make Imports Lighter

Potential payoff: faster CLI tools, tests, notebooks, and short helper runs.

Current problem:

- importing the top-level package can pull in plotting, Bayesian, and
  population-analysis dependencies that are not needed for basic config/model
  inspection.

Improvement:

- keep `dynamite/__init__.py` minimal;
- lazy-load plotting and optional analysis modules;
- move optional dependency imports inside the functions that need them;
- add a small import-time test budget.

Implementation size: small/medium.

Risk: low if public imports are checked with tests.

### IM-009 - Separate Config Parsing From Output Mutation

Potential payoff: safer inspection and easier tests.

Current problem:

- constructing configuration/model objects can inspect, repair, reset, or write
  output state depending on options;
- this makes read-only tooling harder.

Improvement:

Create explicit phases:

1. parse config;
2. validate config;
3. plan output changes;
4. apply output setup/reset;
5. run model stages.

Implementation size: medium/large.

Risk: medium because callers may rely on current side effects.

### IM-010 - Add Active Build Profiles

Potential payoff: reproducible debugging and safer performance comparisons.

Current problem:

- the active Fortran build is optimized for speed;
- reproducible/debug builds would help numerical investigations.

Improvement:

Document or add named build profiles:

- `shared-fast`: current optimized shared library;
- `shared-portable`: no CPU-specific `-march` choice;
- `shared-debug`: bounds checks, backtraces, no fast-math assumptions;
- `clean-generated`: remove generated object/module/shared-library artifacts.

Implementation size: small/medium.

Risk: low if the default target remains unchanged.

## Suggested Order

1. Add per-stage timing manifests.
2. Add output manifests for current binary orbit-library files.
3. Introduce `SolverProblem` and `SolverResult` internally.
4. Cache solver matrix blocks with strict keys.
5. Add stable `model_key`, `orblib_key`, and `solver_key`.
6. Split config parsing from output mutation.
7. Add active Fortran build profiles.
8. Add binary sidecars for large hot-path arrays.
9. Reduce eager imports.

## What Not To Do First

- Do not rewrite the active Fortran orbit-library core before the benchmark and
  manifest coverage is stronger.
- Do not change binary output formats without schema versioning and migration
  or export support.
- Do not add silent fallbacks for missing caches or failed shared-library calls.
- Do not broaden refactors before isolating output-state side effects.
- Do not optimize individual formulas before measuring full workflow time.

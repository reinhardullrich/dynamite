# Project Knowledge

Last updated: 2026-06-02

This file is the canonical current-state overview for the local DYNAMITE fork
at `/home/reinhard/projects/thomas/dynamite`.

## Repository Purpose

This repository is a fork of the upstream DYNAMITE project for local review,
documentation, and modification work.

DYNAMITE stands for DYnamics, Age and Metallicity Indicators Tracing Evolution.
It is a scientific astronomy package for Schwarzschild orbit-superposition and
stellar-population modelling of stellar systems.

## GitHub Remotes

- `origin`: `https://github.com/reinhardullrich/dynamite.git`
- `upstream`: `https://github.com/dynamics-of-stellar-systems/dynamite.git`

Use `origin` for personal fork changes. Use `upstream` only to fetch or merge
changes from the original project.

## Documentation Boundaries

- `docs/`: upstream DYNAMITE Sphinx documentation. Do not put local AI/agent
  notes here.
- `aidocs/`: local AI/agent documentation and generated review notes.
- `AGENTS.md`: root-level agent instructions. It points to this file and
  `aidocs/CHANGES.md`.

## Local AI Documentation

- `aidocs/README.md`: index for local AI/agent documentation.
- `aidocs/KNOWLEDGE.md`: current project state for local agent work.
- `aidocs/CHANGES.md`: append-only change log for local agent work.
- `aidocs/TECHNICAL_DOCUMENTATION.md`: technical explanation of repository
  structure, configuration, runtime flow, model lifecycle, orbit libraries,
  weight solving, outputs, and safe modification boundaries.
- `aidocs/dynamite_overview.md`: high-level overview of the upstream DYNAMITE
  repository.
- `aidocs/dynamite_code_map.md`: map of major DYNAMITE modules and
  responsibilities.
- `aidocs/fortran_orbit_library_engine.md`: detailed analysis of the active
  Fortran orbit-library backend in
  `orblib_fortran/source/orblib_f_new_mirror.f90`,
  including module responsibilities, runtime connections, compute hotspots,
  multiprocessing boundaries, and replacement risks.
- `aidocs/audits/dynamite_python_audit.md`: Python-side static audit findings.
- `aidocs/audits/dynamite_fortran_audit.md`: Fortran-side audit findings.
- `aidocs/audits/dynamite_scientific_correctness_audit.md`: scientific
  correctness audit.
- `aidocs/audits/full-audit-2026-06-01/`: completed full audit run, split by
  repository/build, configuration, physical model, data ingestion, model
  iteration, orbit-library boundary, weight solving, Fortran backend,
  analysis/plotting/coloring, tests/docs, scientific correctness, and
  operational risk. It also includes an improvement-focused continuation in
  `14_improvement_opportunities.md`. Start with `SUMMARY.md` for the
  prioritized results.

## Main Project Layout

- `dynamite/`: upstream Python package. This nested `dynamite/dynamite` layout
  is normal for this Python project and should not be flattened.
- `orblib_fortran/`: active Fortran backend for orbit starts, orbit
  integration, and orbit-library construction. Human-written Fortran source
  lives under `orblib_fortran/source/`, with bundled numerical routine sources
  under `orblib_fortran/source/numerics/` and inactive retained Fortran sources
  under `orblib_fortran/source/unused/`; the supported build target writes only
  the shared library to ignored `orblib_fortran/build/lib/`. Legacy
  `triaxmass*` mass-helper sources are archived and are not part of the active
  build.
- `dynamite/orblib_api.py`: Python-facing orbit-library API facade. It provides
  typed request/result objects, `run_orbit_library()`, and the active
  `fortran_shared_library` backend. The backend calls
  `orblib_fortran/build/lib/liborblib_fortran.so` through `ctypes`; Python
  passes non-bar MGE/orbit/dark-halo settings, orbit starts, PSF tables,
  aperture geometry, histogram settings, binning maps, and output paths as
  typed arrays/scalars. It no longer creates Fortran `infil/` inputs and no
  longer calls Fortran entry points that accept input filenames. The direct
  backend intentionally preserves legacy text-interface precision for
  `parameters_pot` values and `begin` rows, and uses the generated
  `interpolgrid` in the model directory as an internal cache shared by
  orbit-start, tube, and box workers. Binary `datfil/` orbit-library outputs
  remain the active output contract for the existing Python readers and weight
  solvers.
- `tests/`: local pytest baseline for Fortran replacement work. The default
  suite covers fixture contracts, extracted historical workflow facts, small
  Fortran kernel parity checks, and fast coverage for the direct-input
  orbit-library API facade; opt-in slow tests include a generated
  orbit-library LOSVD output comparison against the self-contained NGC6278
  fixture in `tests/fixtures/orblib_losvd/`. The slow LOSVD tests compare one
  generated direct shared-library output both against the historical
  executable-generated fixture with legacy compatibility tolerances and against
  `data/comparison_losvd_shared_library.npz`, a current shared-library fixture
  with tight per-element `1e-12` tolerance.
- `docs/`: upstream Sphinx documentation.
- `archive/dev_tests/`: archived upstream development tests, notebooks, sample
  configurations, and historical fixtures kept for human reference.
- `archive/legacy_nnls_fortran/`: archived legacy NNLS/GALAHAD Fortran solver
  sources and legacy `triaxmass*` mass-helper sources, no longer part of the
  active `orblib_fortran` build. The active runtime rejects
  `LegacyWeightSolver`; use Python `NNLS`.
- `archive/legacy_orbgen_partgen/`: archived untested `orbgen`/`partgen`
  particle/orbit export utilities, no longer part of the active Fortran tree.
- `.github/workflows/ci.yml`: upstream CI workflow.
- `requirements.txt` and `setup.py`: upstream Python packaging inputs.

## Audit Summary

The local audit notes are generated documentation only; they are not upstream
source files.

- Python audit: found packaging, dependency, runtime-validation,
  orbit-library failure-detection, and dark-halo method risks.
- Fortran audit: found legacy failure-handling, solver-status, build-system,
  and uninitialized-data risks.
- Scientific audit: found the core non-rotating triaxial
  Schwarzschild/MGE modelling chain scientifically grounded, with caveats
  around convergence, barred-model benchmarking, cored-log halo density
  domains, and modelling priors.
- Full 2026-06-01 audit: local install succeeded in `.venv/`, no-GALAHAD
  Fortran build succeeded, full GALAHAD-backed Fortran build succeeded after
  repairing generated static archives, pytest collection currently fails, and
  the highest risks are CI coverage gaps, unsafe output-state mutation, weak
  Python-to-Fortran failure detection, solver-result validation gaps, physical
  parameter domain gaps, and non-atomic model/cache writes.
- GALAHAD follow-up: direct solver-mode `5` probes reached QPB in
  `triaxnnls_noCRcut` and `triaxnnls_CRcut`, but both logged
  `QPB_solve exit status = -5` while the shell process exited `0` and output
  files were written. Treat solver-status propagation as a confirmed high-risk
  issue.
- Improvement continuation: `14_improvement_opportunities.md` focuses on
  non-bug-fix changes: lazy imports, binary sidecar caches, prepared NNLS matrix
  caching, stable model/orbit-library keys, explicit timing manifests,
  structured command specs, typed settings wrappers, and smaller stage-specific
  helper functions.

## Separated Workspaces

CiFoS work has been moved out of this repository. It now lives in the sibling
folder `/home/reinhard/projects/thomas/cifos`.

This DYNAMITE fork should contain only DYNAMITE-related source files,
upstream documentation, and local DYNAMITE review notes.

## Human-Run Operational Scripts And Commands

Inspect local changes:

```bash
git status --short
```

Fetch upstream updates:

```bash
git fetch upstream
```

Push fork changes:

```bash
git push origin master
```

## Current Documentation Boundary

For local AI/agent documentation, use `aidocs/`. The upstream `docs/` tree is
reserved for DYNAMITE's Sphinx documentation. The current detailed local guide
is `aidocs/TECHNICAL_DOCUMENTATION.md`.

## Local Install Rule

Dependency setup for audit and development must stay local to this repository.
Use `.venv/` for Python dependencies. Do not use global Python installs, system
package managers, `sudo`, or global compiler/library installation without
asking first.

Current local audit environment:

- Python dependencies are installed in `.venv/`.
- `pip check` passed after the local editable install.
- GNU Fortran 13.3.0 at `/usr/bin/gfortran` was used for the active
  no-GALAHAD Fortran build.
- `orblib_fortran/Makefile` and `orblib_fortran/Makefile.linux` treat the
  shared library as the only supported runtime build product. `make`,
  `make all`, `make nogal`, and `make shared` build
  `orblib_fortran/build/lib/liborblib_fortran.so`; temporary object/module
  directories may exist during compilation but are generated artifacts.
- Use `MPLCONFIGDIR=/tmp/dynamite-mplconfig` for local/headless Matplotlib
  commands to avoid config-cache warnings.
- For future fresh setup, `uv` is acceptable and likely faster, but the current
  completed audit install used `.venv` plus `pip`.

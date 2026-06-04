# Project Knowledge

Last updated: 2026-06-04

This file is the canonical current-state overview for the local DYNAMITE fork
at `/home/reinhard/projects/thomas/dynamite`.

## Repository Purpose

This repository is a fork of the upstream DYNAMITE project for local review,
documentation, and modification work.

DYNAMITE stands for DYnamics, Age and Metallicity Indicators Tracing Evolution.
It is a scientific astronomy package for Schwarzschild orbit-superposition and
stellar-population modelling of stellar systems.

## GitHub Remotes

- `origin`: `git@github.com:reinhardullrich/dynamite.git`
- `upstream`: `https://github.com/dynamics-of-stellar-systems/dynamite.git`

Use `origin` for personal fork changes. Use `upstream` only to fetch or merge
changes from the original project.

## Documentation Boundaries

- `docs/`: upstream DYNAMITE Sphinx documentation. Do not put local AI/agent
  notes here.
- `aidocs/`: local AI/agent documentation and generated review notes.
- `AGENTS.md`: intentionally empty local project instruction file. Active
  user-level agent instructions live outside this repository.

## Local AI Documentation

- `aidocs/INDEX.md`: index for local AI/agent documentation.
- `aidocs/KNOWLEDGE.md`: current project state for local agent work.
- `aidocs/CHANGES.md`: historical local change log. Update it only when a
  human-readable historical record is useful.
- `aidocs/TECHNICAL_DOCUMENTATION.md`: technical explanation of repository
  structure, configuration, runtime flow, model lifecycle, orbit libraries,
  weight solving, outputs, and safe modification boundaries.
- `aidocs/ASTRO_PHYSICS_PROGRAMMING_OVERVIEW.md`: fast conceptual bridge
  between the astronomy/physics ideas and the programming workflow: models,
  orbits, ODE integration, projection, orbit-library data, and NNLS weights.
- `aidocs/dynamite_overview.md`: high-level overview of the upstream DYNAMITE
  repository.
- `aidocs/dynamite_code_map.md`: map of major DYNAMITE modules and
  responsibilities.
- `aidocs/fortran_orbit_library_engine.md`: detailed analysis of the active
  Fortran orbit-library backend that now lives as split modules under
  `orblib_fortran/source/orbit_library/`, including module responsibilities,
  runtime connections, compute hotspots, multiprocessing boundaries, and
  replacement risks.
- `aidocs/fortran_backend_python_contract.md`: operational reference for the
  active Fortran shared-library backend and pointer to the detailed
  `aidocs/fortran/` documentation set.
- `aidocs/fortran/`: detailed agent-facing documentation for the active
  Fortran backend:
  - `INDEX.md`: read order and topic map.
  - `python-contract.md`: Python call graph, shared-library ABI, worker
    isolation, direct input arrays, and precision compatibility.
  - `source-map.md`: active Fortran source files/modules and retained inactive
    sources.
  - `runtime-flow.md`: orbit-start, tube/box runs, DOP853 integration,
    projection, PSF, aperture, LOSVD, qgrid, and output flow.
  - `output-contract.md`: generated `datfil/` files, compression, completion
    markers, cache files, and Python readers.
  - `performance-output-size-review.md`: current static review of Fortran
    runtime optimization and output-size opportunities.
  - `change-guide.md`: high-risk changes, parity requirements, tests, and
    update checklists.
- `aidocs/audits/full-audit-2026-06-04/`: current full audit package, split by
  repository/build, configuration, physical model, data ingestion, model
  iteration, orbit-library boundary, weight solving, Fortran backend,
  analysis/plotting/coloring, tests/docs, scientific correctness, operational
  risk, active runtime verification, improvement opportunities, and active
  NNLS solver policy. Start with `SUMMARY.md` for the prioritized current
  findings.

## Main Project Layout

- `dynamite/`: upstream Python package. This nested `dynamite/dynamite` layout
  is normal for this Python project and should not be flattened.
- `orblib_fortran/`: active Fortran backend for orbit starts, orbit
  integration, and orbit-library construction. Human-written Fortran source
  lives under `orblib_fortran/source/`; larger groups live in `potential/`,
  `orbit_library/`, and `numerics/`, while one-file API, parameter, and
  orbit-start sources stay directly under `source/`; inactive retained
  reference files live under `orblib_fortran/unused/`; the supported build
  target writes only the shared library to ignored `orblib_fortran/build/lib/`.
  `orblib_fortran/unused/` is archive/reference-only. Do not use code
  from `orblib_fortran/unused/` in active builds, refactors, replacement work, tests,
  or new runtime paths unless the user explicitly reverses this rule. Legacy
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
- `tests/`: local pytest baseline for the active orblib Fortran shared-library
  backend, the direct-input Python API facade, and future replacement work. The
  default suite covers fixture contracts, extracted historical workflow facts, small
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

- Full audit package: `aidocs/audits/full-audit-2026-06-04/` is current as of
  2026-06-04. Current high-priority findings are configuration/model
  constructors that mutate output state, non-atomic model/cache/weight writes,
  incomplete Python solver-result validation, physical/log-parameter domain
  validation gaps, tolerance-based model identity checks, and plotting/coloring
  runtime risks.
- Active runtime verification: `13_active_runtime_verification.md` documents
  the current shared-library build, direct Python-input API, binary `datfil/`
  output contract, Python `NNLS` solver contract, pytest coverage, verification
  gaps, and acceptance criteria.
- Improvement continuation: `14_improvement_opportunities.md` focuses on
  current-code improvements: per-stage timing manifests, binary sidecar caches,
  prepared NNLS matrix caching, explicit solver problem/result objects, stable
  model/orbit-library keys, direct shared-library API hardening, binary output
  contract versioning, lighter imports, cleaner config/runtime separation, and
  active build profiles. `15_active_nnls_solver_benchmark.md` now documents the
  active Python `NNLS` solver policy, validation, fixture, caching, and benchmark
  plan only.

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
git push origin <branch>
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
- Current package metadata requires Python 3.10 or newer. CI covers Python
  3.10, 3.11, and 3.12.
- `pip check` passed after the local editable install.
- GNU Fortran 13.3.0 at `/usr/bin/gfortran` was used for the active
  no-GALAHAD Fortran build.
- `orblib_fortran/makefile` and `orblib_fortran/makefile.linux` treat the
  shared library as the only supported runtime build product. `make`,
  `make all`, `make nogal`, and `make shared` build
  `orblib_fortran/build/lib/liborblib_fortran.so`; temporary object/module
  directories may exist during compilation but are generated artifacts.
- Use `MPLCONFIGDIR=/tmp/dynamite-mplconfig` for local/headless Matplotlib
  commands to avoid config-cache warnings.
- For future fresh setup, `uv` is acceptable and likely faster, but the current
  completed audit install used `.venv` plus `pip`.

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
  Fortran orbit-library backend in `legacy_fortran/orblib_f_new_mirror.f90`,
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
- `legacy_fortran/`: legacy Fortran backend for orbit starts, orbit
  integration, orbit-library construction, mass calculations, and legacy
  non-negative least-squares/GALAHAD workflows.
- `tests/`: local pytest baseline for Fortran replacement work. The default
  suite covers fixture contracts, extracted historical workflow facts, and
  small Fortran kernel parity checks; opt-in slow/legacy tests include a
  generated orbit-library LOSVD output comparison against the self-contained
  NGC6278 fixture in `tests/fixtures/orblib_losvd/`.
- `docs/`: upstream Sphinx documentation.
- `archive/dev_tests/`: archived upstream development tests, notebooks, sample
  configurations, and historical fixtures kept for human reference.
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
- GNU Fortran 13.3.0 at `/usr/bin/gfortran` was used for `make nogal`.
- Full GALAHAD-linked `make all` was built locally with
  `GALAHADDIR=legacy_fortran/galahad-2.3` and
  `GALAHADTYPE=pc.lnx.gfo/double` after re-adding generated `gltr.o` and
  `hsl_ma57d.o` to the local GALAHAD static archives.
- Use `MPLCONFIGDIR=/tmp/dynamite-mplconfig` for local/headless Matplotlib
  commands to avoid config-cache warnings.
- For future fresh setup, `uv` is acceptable and likely faster, but the current
  completed audit install used `.venv` plus `pip`.

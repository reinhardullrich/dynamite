# AI Documentation Index

This folder contains local AI/agent documentation for the personal DYNAMITE
fork. It is intentionally separate from upstream `docs/`, which is the
project's Sphinx documentation tree.

## Core Files

- `KNOWLEDGE.md`: current state and local working context for this fork.
- `TECHNICAL_DOCUMENTATION.md`: technical documentation for repository
  structure, runtime flow, model lifecycle, orbit-library generation, weight
  solving, outputs, and safe modification boundaries.
- `ASTRO_PHYSICS_PROGRAMMING_OVERVIEW.md`: fast conceptual bridge between the
  astronomy/physics ideas and the programming workflow: models, orbits, ODE
  integration, projection, orbit-library data, and NNLS weights.
- `CHANGES.md`: historical local change log. Update it only when a
  human-readable historical record is useful.

## Review Notes

- `dynamite_overview.md`: high-level overview of the upstream project.
- `dynamite_code_map.md`: shorter code map and runtime-flow sketch.
- `fortran_orbit_library_engine.md`: detailed analysis of the orbit-library
  engine that now lives as split modules under
  `orblib_fortran/source/orbit_library/`, including runtime connections,
  computational hotspots, multiprocessing boundaries, and replacement risks.
- `fortran_backend_python_contract.md`: operational reference for the active
  Fortran shared-library backend and pointer to the detailed Fortran
  documentation set.
- `fortran/`: detailed agent-facing documentation for the active Fortran
  backend:
  - `fortran/INDEX.md`: read order and topic map.
  - `fortran/python-contract.md`: Python call graph, shared-library ABI,
    worker isolation, direct input arrays, and precision compatibility.
  - `fortran/source-map.md`: active Fortran files/modules and retained
    inactive sources.
  - `fortran/runtime-flow.md`: orbit-start, tube/box runs, integration,
    projection, PSF, aperture, LOSVD, qgrid, and output flow.
  - `fortran/output-contract.md`: generated `datfil/` files, compression,
    completion markers, cache files, and Python readers.
  - `fortran/performance-output-size-review.md`: static optimization and
    output-size review for active Fortran runtime and qgrid/LOSVD files.
  - `fortran/change-guide.md`: high-risk changes, parity requirements, tests,
    and update checklists.
- `audits/dynamite_python_audit.md`: Python-side audit notes.
- `audits/dynamite_fortran_audit.md`: Fortran-side audit notes.
- `audits/dynamite_scientific_correctness_audit.md`: scientific-correctness
  audit notes.
- `audits/full-audit-2026-06-01/`: full audit package. Start with
  `SUMMARY.md`.

## Boundary

Do not store local AI notes in upstream `docs/`. Put new AI-facing Markdown in
this folder unless the user explicitly asks to modify the upstream docs.

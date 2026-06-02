# AI Documentation Index

This folder contains local AI/agent documentation for the personal DYNAMITE
fork. It is intentionally separate from upstream `docs/`, which is the
project's Sphinx documentation tree.

## Core Files

- `KNOWLEDGE.md`: current state and local working rules for this fork.
- `CHANGES.md`: append-only local change log.
- `TECHNICAL_DOCUMENTATION.md`: technical documentation for repository structure,
  runtime flow, model lifecycle, orbit-library generation, weight solving,
  outputs, and safe modification boundaries.

## Review Notes

- `dynamite_overview.md`: high-level overview of the upstream project.
- `dynamite_code_map.md`: shorter code map and runtime-flow sketch.
- `fortran_orbit_library_engine.md`: detailed analysis of
  `orblib_fortran/source/orblib_f_new_mirror.f90`, its runtime connections,
  computational hotspots, multiprocessing boundaries, and replacement risks.
- `cpp_orblib_port_plan.md`: C++ orbit-library backend port rules, including
  correctness-first/performance-second constraints, DOP853 policy, allocation
  rules, fixture-based acceptance criteria, and benchmark policy.
- `audits/dynamite_python_audit.md`: Python-side audit notes.
- `audits/dynamite_fortran_audit.md`: Fortran-side audit notes.
- `audits/dynamite_scientific_correctness_audit.md`: scientific-correctness
  audit notes.

## Boundary

Do not store local AI notes in upstream `docs/`. Put new AI-facing Markdown in
this folder unless the user explicitly asks to modify the upstream docs.

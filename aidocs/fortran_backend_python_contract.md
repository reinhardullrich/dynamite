# Fortran Backend And Python Contract

Last updated: 2026-06-04

Purpose: top-level entry point for agent-facing documentation about the active
DYNAMITE Fortran orbit-library backend and its Python runtime contract.

Detailed material now lives under `aidocs/fortran/`. Start there for new work:

- `aidocs/fortran/INDEX.md`: read order and topic map.
- `aidocs/fortran/python-contract.md`: Python call graph, `ctypes` ABI,
  worker-process isolation, direct input arrays, and precision compatibility.
- `aidocs/fortran/source-map.md`: active Fortran source files, major modules,
  retained inactive sources, and what each file is responsible for.
- `aidocs/fortran/runtime-flow.md`: orbit-start generation, tube/box orbit
  library runs, DOP853 integration, projection, PSF, aperture, LOSVD, qgrid,
  and output flow.
- `aidocs/fortran/output-contract.md`: generated `datfil/` files, binary
  record contracts, Python readers, compression, done markers, and cache files.
- `aidocs/fortran/change-guide.md`: high-risk changes, parity requirements,
  test commands, and update checklists.

Important current facts:

- Active backend library:
  `orblib_fortran/build/lib/liborblib_fortran.so`.
- Supported build command: `make -C orblib_fortran shared`.
- Active Python facade: `dynamite/orblib_api.py`.
- Backend name: `fortran_shared_library`.
- ABI version: `2`.
- Active direct ABI entry points:
  `orblib_api_run_orbitstart_memory` and
  `orblib_api_run_orblib_direct`.
- The active direct ABI supports the non-bar triaxial path. Bar-specific
  Fortran code exists, but is not wired through the direct Python backend.
- Python still reads the generated binary `datfil/` orbit-library outputs
  through `dynamite.orblib.LegacyOrbitLibrary`.


# Fortran Backend Documentation Index

Last updated: 2026-06-04

Scope: active Fortran orbit-library backend, the Python shared-library facade,
and the generated files consumed by the Python orbit-library readers and weight
solvers.

Do not treat this folder as human-facing upstream documentation. It is
agent-facing source-of-truth material for changing, profiling, or replacing the
Fortran backend safely.

## Read Order

1. `python-contract.md`: start here when touching Python/Fortran boundaries.
2. `source-map.md`: read before editing Fortran files.
3. `runtime-flow.md`: read before profiling, replacing, or changing numeric
   behavior.
4. `output-contract.md`: read before changing generated files, compression,
   readers, done markers, or caches.
5. `performance-output-size-review.md`: read before optimizing Fortran runtime
   paths or changing qgrid/LOSVD/pops output size.
6. `change-guide.md`: read before implementation work.

## Fast Orientation

The active backend is not a standalone Fortran executable workflow anymore.
Python calls a shared library:

```text
dynamite/orblib_api.py
  -> ctypes
  -> orblib_fortran/build/lib/liborblib_fortran.so
  -> orblib_fortran/source/orblib_c_api.f90
  -> orblib_fortran/source/orbit_library/*.f90
```

The Fortran backend generates binary orbit-library files in each model's
`datfil/` directory. Python then reads those files with
`dynamite.orblib.LegacyOrbitLibrary` and passes the resulting orbit matrices to
the Python `NNLS` weight-solver path.

## Current Supported Backend Shape

- Build artifact: `orblib_fortran/build/lib/liborblib_fortran.so`.
- Build command: `make -C orblib_fortran shared`.
- Python backend name: `fortran_shared_library`.
- Shared-library ABI version: `2`.
- Active ABI entry points:
  - `orblib_api_abi_version`
  - `orblib_api_run_orbitstart_memory`
  - `orblib_api_run_orblib_direct`
- Active direct runtime: non-bar triaxial orbit library.
- Archived legacy weight solver: `archive/legacy_nnls_fortran/`.
- Archived development scripts: `archive/dev_tests/`.

## Related Agent Docs

- `aidocs/fortran_backend_python_contract.md`: short top-level pointer to this
  documentation set.
- `aidocs/fortran_orbit_library_engine.md`: earlier long-form engine analysis,
  including replacement risks and performance notes.
- `aidocs/TECHNICAL_DOCUMENTATION.md`: full repository technical overview.
- `aidocs/audits/full-audit-2026-06-01/13_active_runtime_verification.md`:
  audit-era verification of the active runtime.
- `aidocs/audits/full-audit-2026-06-01/15_active_nnls_solver_benchmark.md`:
  solver policy and NNLS benchmark context.

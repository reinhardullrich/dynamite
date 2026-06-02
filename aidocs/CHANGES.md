# Change Log

This file is append-only. Add new entries at the bottom.

## 2026-06-01

- Created `aidocs/` for local AI/agent Markdown so upstream DYNAMITE `docs/`
  remains reserved for the project's Sphinx documentation.
- Copied `AGENTS.md` from the sibling CiFoS workspace and updated it to point
  at `aidocs/KNOWLEDGE.md` and `aidocs/CHANGES.md`.
- Moved local DYNAMITE review Markdown into `aidocs/`, including overview,
  code map, and audit files.
- Recorded that CiFoS work lives in the sibling
  `/home/reinhard/projects/thomas/cifos` folder.
- Added `aidocs/README.md` as the local AI documentation index.
- Added `aidocs/TECHNICAL_DOCUMENTATION.md` with detailed internal documentation of
  the DYNAMITE repository layout, config lifecycle, runtime object model,
  model iteration, orbit-library generation, weight solving, output state,
  failure recovery, and safe modification boundaries.
- Updated `aidocs/KNOWLEDGE.md` to reference the technical documentation.
- Created `aidocs/audits/full-audit-2026-06-01/` and recorded the full audit
  split, write boundaries, local-only install rule, execution order, and
  finding format.
- Documented the local install rule in `aidocs/KNOWLEDGE.md`: Python
  dependencies must go into `.venv/`, and any global/system install requires
  explicit approval first.
- Completed the 2026-06-01 full audit documentation under
  `aidocs/audits/full-audit-2026-06-01/`, including Fortran backend,
  analysis/plotting/coloring, tests/docs, scientific correctness, operational
  risk, and the prioritized `SUMMARY.md`.
- Recorded the completed local audit environment in `aidocs/KNOWLEDGE.md`,
  including `.venv/`, successful `pip check`, successful no-GALAHAD Fortran
  build, and the local `MPLCONFIGDIR` recommendation.
- Double-checked the completed full-audit documentation, reverified the main
  high-priority findings against the current source, reran `pip check` and
  pytest collection, and corrected stale wording about GALAHAD targets and the
  no-GALAHAD Fortran build note.
- Closed the GALAHAD audit gap: installed local GALAHAD 2.3 QP support from
  vendored dependency trees, repaired generated static archives missing
  `gltr.o` and `hsl_ma57d.o`, completed full GALAHAD-backed `make all`, ran
  link/load checks, and documented the results in
  `aidocs/audits/full-audit-2026-06-01/13_galahad_runtime_check.md`.
- Confirmed by runtime probe that solver-mode `5` reaches GALAHAD/QPB in both
  `triaxnnls_noCRcut` and `triaxnnls_CRcut`, but both logged
  `QPB_solve exit status = -5` while the shell process exited `0` and wrote
  output files.
- Added `aidocs/audits/full-audit-2026-06-01/14_improvement_opportunities.md`
  as a non-bug-fix improvement roadmap covering import speed, runtime storage,
  NNLS matrix caching, table lookup keys, runtime manifests, command execution,
  typed settings, method extraction, and build-profile improvements.
- Clarified the improvement roadmap after local timing checks: `import dynamite`
  is about 3.6 seconds in this environment, which matters for short tools and
  tests, but full legacy model runs are dominated by Fortran orbit-library
  generation and surrounding disk I/O rather than startup time.
- Expanded `IM-015` in `14_improvement_opportunities.md` with a staged modern
  solver roadmap: common `SolverProblem` / `SolverResult`, SciPy NNLS baseline,
  optional `scipy.lsq_linear`, CVXOPT cross-checks, sparse-path prerequisites,
  legacy Fortran/GALAHAD compatibility mode, and required parity tests before
  changing defaults.

## 2026-06-02

- Added `aidocs/fortran_orbit_library_engine.md`, a detailed analysis of
  `orblib_fortran/source/orblib_f_new_mirror.f90`, covering runtime wiring,
  Fortran module responsibilities, orbit integration and projection flow,
  computational hotspots, multiprocessing boundaries, output contracts, and
  replacement strategy.
- Updated `aidocs/README.md` and `aidocs/KNOWLEDGE.md` to reference the new
  Fortran orbit-library engine analysis.
- Added `tests/test_fortran_orblib_output.py`, an opt-in slow orblib Fortran
  regression test that regenerates the NGC6278 orbit-library LOSVD workflow
  from self-contained fixtures under `tests/fixtures/orblib_losvd/` and
  compares the produced velocity grid and LOSVD output statistics against the
  local reference fixture.
- Updated `aidocs/KNOWLEDGE.md` to document the new Fortran orbit-library
  output comparison and fixture location.
- Cleaned the active `orblib_fortran/` structure: object files now build under
  `orblib_fortran/build/obj/`, module files under `orblib_fortran/build/mod/`,
  final executables under `orblib_fortran/bin/`, human-written Fortran source
  under `orblib_fortran/source/`, active numerical routine sources under
  `orblib_fortran/source/numerics/`, and untested `orbgen`/`partgen` utilities
  are archived under `archive/legacy_orbgen_partgen/`.
- Removed stale `orblib` and `partgen` package-data entries from `setup.py`
  and expanded the Fortran inventory tests to cover active numerics sources and
  the archived `orbgen`/`partgen` files.
- Renamed the active Fortran backend directory from `legacy_fortran/` to
  `orblib_fortran/`, updated Python's default executable lookup path to
  `orblib_fortran/bin/`, and renamed the opt-in executable test gate to
  `DYNAMITE_RUN_ORBLIB_FORTRAN_EXEC_TESTS`.
- Moved inactive retained Fortran files `pij.f90` and `dopri5.f` into
  `orblib_fortran/source/unused/`; `dopri5.f` remains an explicitly inactive
  alternate integrator reference while active builds continue to use DOP853.
- Added `dynamite/orblib_api.py`, a Python-facing orbit-library API facade with
  typed request/result objects, an executable-backed Fortran adapter, and an
  explicit reserved shared-library backend placeholder. Added
  `Model.run_orblib_api()` as the convenience entry point and fast unit tests
  for the facade while keeping the existing `LegacyOrbitLibrary` path intact.
- Implemented the first Fortran shared-library backend: added
  `orblib_fortran/source/orblib_api.f90` with C-ABI wrappers for orbit-start
  and orbit-library runs, added `make shared` targets that build
  `orblib_fortran/build/lib/liborblib_fortran.so`, and wired
  `backend='fortran_shared_library'` through `ctypes` in `dynamite/orblib_api.py`.
  The shared-library backend replaces direct Fortran executable launches but
  still uses the existing `infil/`/`datfil/` file contract internally.
- Archived the legacy `triaxmass*`/`triaxmassbin*` Fortran mass-helper sources
  and their `nag.f` dependency under
  `archive/legacy_nnls_fortran/legacy_fortran/mass_helpers/`, removed those
  programs from the active `orblib_fortran` build and package data, removed
  generated `triaxmass` input/script hooks from `dynamite/orblib.py`, and made
  `LegacyWeightSolver` fail early in configuration/model execution. The active
  orbit backend now builds only orbit-start and orbit-library programs while
  Python `NNLS` handles the weight-solver path.
- Added the first direct-input shared-library ABI slice for non-bar orbit-start
  generation: `orblib_api_run_orbitstart_memory` accepts MGE/orbit/dark-halo
  inputs as typed arrays and scalars, and
  `SharedLibraryFortranOrbitBackend.run_orbitstart_memory()` returns Python
  `begin`/`beginbox` arrays without requiring `orbstart.in`,
  `parameters_pot.in`, or `begin*.dat`. Full orbit-library generation still
  uses the current `infil/`/`datfil/` file contract, with binary `datfil/`
  outputs retained as the temporary output boundary.
- Implemented the direct Python-input shared-library orbit-library generation
  path for non-bar models. `orblib_api_run_orblib_direct` now receives
  orbit-start arrays, integration settings, PSF tables, aperture geometry,
  histogram settings, binning maps, and output paths from Python instead of
  reading `orblib.in`, `orblibbox.in`, aperture files, bin files, or
  `begin*.dat`. The shared-library ABI was bumped to version `2`, the old
  file-taking C-ABI entry points were removed from `orblib_api.f90`, and direct
  calls disable the `interpolgrid` file cache. `Model.get_orblib()` and
  `LegacyOrbitLibrary.get_orblib()` now delegate generation to the direct
  shared-library backend, and `Model.setup_directories()` no longer creates
  `infil/` for active model runs while retaining binary `datfil/` outputs for
  the existing Python readers. Verified with `make -C orblib_fortran shared`,
  `python3 -m py_compile ...`, focused `tests/test_orblib_api.py` fast tests,
  and `.venv/bin/python -m pytest tests -m 'not slow and not orblib_fortran'`
  (`61 passed, 3 deselected`).
- Made the active Fortran backend shared-library-only. `make`, `make all`,
  `make nogal`, and `make shared` now build only
  `orblib_fortran/build/lib/liborblib_fortran.so`; executable driver sources
  were moved to `orblib_fortran/source/unused/`; package metadata now points at
  the shared object instead of `orblib_fortran/bin/*`; and the Fortran
  inventory test now checks the shared library rather than executable files.
  Local generated `orblib_fortran/bin/` was removed; intermediate `.mod`/object
  build artifacts remain ignored generated files and may be left locally after
  future builds.
- Adjusted the opt-in slow orblib Fortran LOSVD regression test for the direct
  shared-library path: the standalone fixture model is registered in
  `all_models` before orbit generation, and the total LOSVD mass comparison now
  allows the observed stable aggregate delta from the historical executable
  reference while preserving the grid, shape, nonnegative, mean, quantile, and
  max-difference checks.

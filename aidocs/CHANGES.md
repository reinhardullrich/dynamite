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
- Fixed the direct shared-library orbit-library numerical parity issue: the
  orbit-start worker now runs in the model directory so tube and box workers
  reuse the same generated `interpolgrid`, direct Python inputs preserve the
  historical `parameters_pot.in` decimal precision, and direct begin rows are
  internally round-tripped through the legacy `ES30.10` precision without
  reintroducing Fortran input files. Restored the slow LOSVD fixture aggregate
  tolerance from `5e-4` to `2e-4`.
- Added a separate current-backend LOSVD parity fixture at
  `tests/fixtures/orblib_losvd/data/comparison_losvd_shared_library.npz` and a
  second opt-in slow Fortran test that compares regenerated direct
  shared-library output against it with per-element `1e-12` tolerance. The
  historical executable-generated fixture test remains separate and keeps its
  legacy compatibility tolerance.
- Documented the direct shared-library precision compatibility problem in
  `aidocs/fortran_orbit_library_engine.md` and updated
  `aidocs/TECHNICAL_DOCUMENTATION.md` to reflect the current behavior: legacy
  `parameters_pot`/`begin` text precision is intentionally preserved and the
  generated `interpolgrid` cache is shared by orbit-start, tube, and box
  workers.
- Audited and updated Markdown documentation for the current `fortran-cleanup`
  branch state. Active docs and audit reports now describe the shared-library
  orblib backend, SSH origin remote, archived `archive/dev_tests/` workflows,
  archived legacy NNLS/GALAHAD and mass-helper code, rejected
  `LegacyWeightSolver`, current pytest baseline under `tests/`, and the
  direct shared-library LOSVD parity fixtures.
- Rewrote full-audit chapters 14 and 15 to cover only current active code:
  shared-library orblib generation, Python `NNLS`, active solver validation,
  caching, benchmark manifests, and current pytest fixture strategy. Removed
  retired solver-code descriptions from those chapters, renamed chapter 15 to
  `15_active_nnls_solver_benchmark.md`, and updated the audit README/SUMMARY
  references accordingly.
- Rewrote full-audit chapter 13 as current active runtime verification only,
  renamed it to `13_active_runtime_verification.md`, and updated the audit
  README, SUMMARY, environment reference, and canonical knowledge summary to
  point at the active shared-library/orblib/NNLS verification contract.
- Added `aidocs/cpp_orblib_port_plan.md` for the `fortran-to-cpp` branch,
  recording the C++ orbit-library port policy: correctness before speed,
  aggressive optimization only after parity, no avoidable hot-path allocations,
  DOP853 dense-output preservation, RHS/acceleration optimization, existing
  Fortran fixtures as acceptance tests, and stage-split benchmark requirements.
- Added the first experimental C++ orbit-library backend slice: `orblib_cpp/`
  now builds `build/lib/liborblib_cpp.so` with ABI version `1`, exports
  C-compatible orbit-start and orbit-library entry-point stubs that return
  not-implemented status `-100`, and `dynamite/orblib_api.py` accepts backend
  name `cpp_shared_library` while keeping `fortran_shared_library` as the
  default. Added focused pytest coverage for C++ source inventory, ABI version,
  read-only backend behavior, missing-library failure, and explicit
  not-implemented generation status.
- Ported the first active Fortran numerical kernel to C++: `ran1_nr.f` is now
  represented by `dynamite::orblib_cpp::Ran1` in `orblib_cpp/include/ran1.hpp`
  and `orblib_cpp/source/ran1.cpp`. Added C ABI helper
  `orblib_cpp_api_ran1_sequence` and opt-in pytest coverage comparing the C++
  sequence against the existing Python/Fortran reference sequence to `1e-15`.
- Ported the active DOP853 numerical integrator to C++ as
  `dynamite::orblib_cpp::Dop853` in `orblib_cpp/include/dop853.hpp` and
  `orblib_cpp/source/dop853.cpp`. The implementation preserves the Fortran
  coefficient table, adaptive controller, dense-output polynomial, status
  codes, and step/function counters while using reusable work arrays allocated
  before the integration loop. Added test-only C ABI helper
  `orblib_cpp_api_dop853_harmonic` and opt-in pytest coverage validating
  harmonic-oscillator final state and dense-output samples to `5e-12`.
- Ported the next C++ potential-setup dependencies: `numerics/ellipint.f90`
  is represented by C++ Carlson/Legendre elliptic integrals in
  `orblib_cpp/include/elliptic_integrals.hpp` and
  `orblib_cpp/source/elliptic_integrals.cpp`, and the non-bar
  `iniparam_from_arrays()`/`tp_setup()` MGE setup formulas are represented by
  `dynamite::orblib_cpp::TriaxialMgeSetup` in
  `orblib_cpp/include/triaxial_mge.hpp` and
  `orblib_cpp/source/triaxial_mge.cpp`. Added test-only ABI helpers
  `orblib_cpp_api_elliptic_legendre` and
  `orblib_cpp_api_triaxial_mge_setup`, with opt-in pytest coverage against
  SciPy elliptic integrals and the Fortran MGE setup formulas.
- Ported the stellar triaxial MGE potential/acceleration evaluator from
  `tp_potent()`/`tp_accel()` into `orblib_cpp/source/triaxial_mge.cpp`,
  covering the inner approximation, adaptive mid-radius quadrature, and outer
  point-mass branches. Added test-only ABI helper
  `orblib_cpp_api_triaxial_mge_evaluate` and opt-in pytest coverage comparing
  representative branch points against independent Python/SciPy calculations
  of the Fortran formulas.
- Ported the next C++ potential-stack slice from `dmpotent.f90`: the
  Plummer-style black-hole contribution and dark-halo profiles 0 through 3
  (`no halo`, NFW, Hernquist, and triaxial cored logarithmic). Added
  `orblib_cpp/include/potential.hpp`, `orblib_cpp/source/potential.cpp`, and
  test-only ABI helper `orblib_cpp_api_potential_stack_evaluate`, with opt-in
  pytest coverage comparing combined stellar MGE, black-hole, and supported
  dark-halo terms against independent Python/SciPy calculations of the Fortran
  formulas. gNFW profile 5 remains unported pending the beta-function helper
  stack.
- Ported the in-memory acceleration interpolation math from
  `interpolpotent.f90` to C++ as
  `dynamite::orblib_cpp::InterpolatedPotential` in
  `orblib_cpp/include/interpolated_potential.hpp` and
  `orblib_cpp/source/interpolated_potential.cpp`. The implementation preserves
  the Fortran radius range formulas, spherical-octant grid construction,
  endpoint angle offsets, log-acceleration storage, trilinear interpolation,
  and direct acceleration fallback outside the interpolation range. Added
  test-only ABI helper `orblib_cpp_api_interpolated_potential_evaluate` and
  opt-in pytest coverage against an independent Python implementation of the
  Fortran grid formulas. The legacy `interpolgrid` disk-cache read/write
  behavior remains unported.
- Ported the orbit RHS derivative formula from `orblib_f_new_mirror.f90`'s
  `derivs` to C++ as `dynamite::orblib_cpp::evaluate_orbit_rhs` in
  `orblib_cpp/include/orbit_rhs.hpp` and `orblib_cpp/source/orbit_rhs.cpp`.
  The implementation uses the C++ interpolated acceleration path and preserves
  both the non-rotating derivative assignment and the barred-frame `Omega`
  terms. Added test-only ABI helper `orblib_cpp_api_orbit_rhs_evaluate` and
  opt-in pytest coverage against independent Python calculations of the
  Fortran formulas.
- Added single-orbit final-state DOP853 integration using the C++ orbit RHS as
  `dynamite::orblib_cpp::integrate_orbit_final_state` in
  `orblib_cpp/include/orbit_integrator.hpp` and
  `orblib_cpp/source/orbit_integrator.cpp`. Added test-only ABI helper
  `orblib_cpp_api_integrate_orbit_final_state` and opt-in pytest coverage
  comparing the final state against SciPy DOP853 on an independent softened
  black-hole RHS. Dense-output orbit sampling, classification, projection,
  LOSVD/qgrid accumulation, and output writing remain unported.
- Added prescribed dense-output sample extraction for single-orbit C++
  integration using the C++ DOP853 dense-output polynomial and orbit RHS as
  `dynamite::orblib_cpp::integrate_orbit_samples`. Added test-only ABI helper
  `orblib_cpp_api_integrate_orbit_samples` and opt-in pytest coverage
  comparing final state plus sampled six-component orbit states against SciPy
  DOP853 dense output on an independent softened black-hole RHS. Orbit
  classification, projection, LOSVD/qgrid accumulation, and output writing
  remain unported.
- Ported dark-halo profile 5 gNFW support into the C++ potential stack in
  `orblib_cpp/source/potential.cpp`, including the Fortran
  `specfunc_beta.f90` unregularized incomplete-beta helper stack, gNFW
  setup normalization, potential, and acceleration formulas. Extended the
  opt-in C++ potential-stack pytest coverage to validate gamma branches below,
  equal to, and above `1` against independent Python calculations of the
  Fortran formulas. The remaining C++ orbit-library gaps are now
  interpolation-grid disk caching if required for parity, orbit-start
  generation, classification, projection/PSF/aperture mapping, LOSVD/qgrid
  accumulation, and binary output writing.
- Ported the Fortran `integrator_find_orbtype()` orbit classification and
  moment formulas into C++ as `dynamite::orblib_cpp::classify_orbit_samples`
  in `orblib_cpp/include/orbit_classification.hpp` and
  `orblib_cpp/source/orbit_classification.cpp`. Added test-only ABI helper
  `orblib_cpp_api_classify_orbit_samples` and opt-in pytest coverage for all
  five orbit type outcomes plus the five `moments` and three `moments2` values
  against a Python mirror of the Fortran formulas. The remaining C++
  orbit-library gaps are now interpolation-grid disk caching if required for
  parity, orbit-start generation, projection/PSF/aperture mapping,
  LOSVD/qgrid accumulation, and binary output writing.
- Ported the Fortran `project_n()` per-symmetry projection and line-of-sight
  velocity formulas into C++ as
  `dynamite::orblib_cpp::project_orbit_samples` in
  `orblib_cpp/include/orbit_projection.hpp` and
  `orblib_cpp/source/orbit_projection.cpp`. Added test-only ABI helper
  `orblib_cpp_api_project_orbit_samples` and opt-in pytest coverage comparing
  projected coordinates and LOS velocities against a Python mirror of the
  Fortran formulas for all five orbit types, all eight projection symmetries,
  and both non-rotating and rotating-frame sign-table paths. The remaining C++
  orbit-library gaps are now interpolation-grid disk caching if required for
  parity, orbit-start generation, PSF/aperture mapping, LOSVD/qgrid
  accumulation, and binary output writing.
- Ported the Fortran PSF Gaussian convolution paths into C++ as
  `dynamite::orblib_cpp::apply_psf_to_projected_samples` in
  `orblib_cpp/include/orbit_psf.hpp` and `orblib_cpp/source/orbit_psf.cpp`.
  Added test-only ABI helper `orblib_cpp_api_apply_psf` and opt-in pytest
  coverage comparing tiny single-Gaussian copy-through, resolved
  single-Gaussian convolution, and weighted MGE-PSF convolution against a
  Python mirror of the Fortran `psf_gaussian()` and `psf_sigma_map()` formulas.
  The remaining C++ orbit-library gaps are now interpolation-grid disk caching
  if required for parity, orbit-start generation, aperture mapping, LOSVD/qgrid
  accumulation, and binary output writing.
- Ported the Fortran `aperture_boxed_find()` boxed-aperture pixel lookup into
  C++ as `dynamite::orblib_cpp::find_boxed_aperture_pixels` in
  `orblib_cpp/include/orbit_aperture.hpp` and
  `orblib_cpp/source/orbit_aperture.cpp`. Added test-only ABI helper
  `orblib_cpp_api_find_boxed_aperture_pixels` and opt-in pytest coverage
  comparing conversion-factor scaling, strict aperture boundaries, bin
  transitions, and 1-based flattened pixel IDs against a Python mirror of the
  Fortran formula. The remaining C++ orbit-library gaps are now
  interpolation-grid disk caching if required for parity, orbit-start
  generation, LOSVD/qgrid accumulation, and binary output writing.
- Ported the Fortran `histogram_velbin()` and `histogram_store()` LOSVD
  velocity-bin and per-aperture histogram accumulation formulas into C++ as
  `dynamite::orblib_cpp::map_losvd_velocity_bins` and
  `dynamite::orblib_cpp::accumulate_losvd_histogram` in
  `orblib_cpp/include/orbit_histogram.hpp` and
  `orblib_cpp/source/orbit_histogram.cpp`. Added test-only ABI helpers
  `orblib_cpp_api_losvd_velocity_bins` and
  `orblib_cpp_api_accumulate_losvd_histogram` with opt-in pytest coverage for
  velocity clamp behavior, strict bin-boundary handling, zero aperture-pixel
  skipping, and normalization-counter increments. Remaining C++ gaps now
  include interpolation-grid disk caching if required for parity, orbit-start
  generation, LOSVD bin-order normalization/output, qgrid accumulation, and
  binary output writing.
- Ported the Fortran LOSVD bin-order collapse, normalization, and sparse
  row-range preparation formulas from `binning_add_it_up()`,
  `histogram_write()`, and `histogram_write_compat_sparse()` into
  `orblib_cpp/source/orbit_histogram.cpp` as
  `dynamite::orblib_cpp::collapse_losvd_binning`,
  `dynamite::orblib_cpp::normalize_losvd_histogram`, and
  `dynamite::orblib_cpp::compute_sparse_losvd_ranges`. Added test-only ABI
  helpers `orblib_cpp_api_collapse_losvd_binning`,
  `orblib_cpp_api_normalize_losvd_histogram`, and
  `orblib_cpp_api_sparse_losvd_ranges` with opt-in pytest coverage for
  bin-order `0` discard, many-to-one bin summation, normalization, sparse
  begin/end offsets, and empty-row sentinels. Remaining C++ gaps now include
  interpolation-grid disk caching if required for parity, orbit-start
  generation, qgrid accumulation, full orbit-engine wiring, and binary output
  writing.
- Ported the Fortran intrinsic qgrid boundary setup, octant-folded moment
  accumulation, orbit-type channel accumulation, and normalization formulas
  from `qgrid_setup()`, `qgrid_store()`, and `qgrid_write()` into
  `orblib_cpp/include/orbit_qgrid.hpp` and
  `orblib_cpp/source/orbit_qgrid.cpp`. Added test-only ABI helpers
  `orblib_cpp_api_qgrid_boundaries`, `orblib_cpp_api_accumulate_qgrid`, and
  `orblib_cpp_api_normalize_qgrid` with opt-in pytest coverage for Fortran
  boundary formulas, `hunt`-style bin equality behavior, non-rotating and
  rotating-frame sign tables, positive-octant filtering, 16-channel
  accumulation, orbit-type channels, and qgrid normalization. Remaining C++
  gaps now include interpolation-grid disk caching if required for parity,
  orbit-start generation, full orbit-engine wiring, and binary output writing.
- Ported qgrid Fortran-record binary serialization into C++ as
  `dynamite::orblib_cpp::write_qgrid_file` in
  `orblib_cpp/include/orbit_output.hpp` and
  `orblib_cpp/source/orbit_output.cpp`. Added test-only ABI helper
  `orblib_cpp_api_write_qgrid_file` and opt-in pytest coverage that writes a
  split `*_qgrid.dat`-style file and reads it back with SciPy `FortranFile`,
  validating the integrator header, qgrid header, boundary records, per-orbit
  headers, orbit-type arrays, and qgrid payload order. Remaining C++ gaps now
  include interpolation-grid disk caching if required for parity, orbit-start
  generation, full orbit-engine wiring, and LOSVD/pops/orbclass output
  writing.
- Ported sparse LOSVD Fortran-record binary serialization into C++ as
  `dynamite::orblib_cpp::write_losvd_histogram_file` in
  `orblib_cpp/include/orbit_output.hpp` and
  `orblib_cpp/source/orbit_output.cpp`. Added test-only ABI helper
  `orblib_cpp_api_write_losvd_histogram_file` and opt-in pytest coverage that
  writes a split `*_losvd_hist.dat`-style file and reads it back with SciPy
  `FortranFile`, validating the mixed histogram setup record, per-row sparse
  begin/end records, skipped empty rows, and optional velocity-bin value
  records. Remaining C++ gaps now include interpolation-grid disk caching if
  required for parity, orbit-start generation, full orbit-engine wiring, and
  pops/orbclass output writing.
- Ported population projected-mass and formatted orbit-class output writing
  into C++ as `dynamite::orblib_cpp::write_population_mass_file` and
  `dynamite::orblib_cpp::write_orbit_class_file` in
  `orblib_cpp/include/orbit_output.hpp` and
  `orblib_cpp/source/orbit_output.cpp`. Added test-only ABI helpers
  `orblib_cpp_api_write_population_mass_file` and
  `orblib_cpp_api_write_orbit_class_file` with opt-in pytest coverage that
  validates `*_pops.dat` records through SciPy `FortranFile` and validates
  `*.dat_orbclass.out` token order against the current Python
  `reshape(..., order='F')` reader contract. Remaining C++ gaps now include
  interpolation-grid disk caching if required for parity, orbit-start
  generation, and full orbit-engine wiring.
- Ported the direct-potential orbit-start `calc_startpos()` and `findReq()`
  kernels from `orbitstart_f.f90` into C++ as
  `dynamite::orblib_cpp::calculate_orbit_start_state` and
  `dynamite::orblib_cpp::find_equivalent_radius` in
  `orblib_cpp/include/orbit_start.hpp` and
  `orblib_cpp/source/orbit_start.cpp`. Added test-only ABI helpers
  `orblib_cpp_api_orbitstart_calc_start_state` and
  `orblib_cpp_api_orbitstart_find_equivalent_radius` with opt-in pytest
  coverage for x/z start placement, positive-y velocity construction,
  negative-kinetic-energy fallback, and the Fortran bisection stopping rule.
  Remaining C++ gaps now include interpolation-grid disk caching if required
  for parity, full orbit-start boundary search/array generation, and full
  orbit-engine wiring.
- Ported the pure orbit-start scheduling kernels `find_unregorbits()` and the
  radius/noreg part of `make_startpoints()` from `orbitstart_f.f90` into C++
  as `dynamite::orblib_cpp::compute_unregularized_orbit_grid` and
  `dynamite::orblib_cpp::compute_tube_start_schedule` in
  `orblib_cpp/include/orbit_start.hpp` and
  `orblib_cpp/source/orbit_start.cpp`. Added test-only ABI helpers
  `orblib_cpp_api_orbitstart_unregularized_grid` and
  `orblib_cpp_api_orbitstart_tube_schedule` with opt-in pytest coverage for
  the reverse `nI2` propagation scan, irregular-energy boundary replacement,
  nearly closed-boundary radius sampling, and the exact Fortran
  `maxval(irregular) == i` noreg flag condition. Remaining C++ gaps now
  include interpolation-grid disk caching if required for parity, full
  orbit-start boundary search/state-array generation, and full orbit-engine
  wiring.
- Ported the per-record box-start path from `make_boxstartpoints()` into C++
  as `dynamite::orblib_cpp::calculate_box_start_record` in
  `orblib_cpp/include/orbit_start.hpp` and
  `orblib_cpp/source/orbit_start.cpp`. Added test-only ABI helper
  `orblib_cpp_api_orbitstart_box_start_record` with opt-in pytest coverage for
  the Fortran one-based `Pi/2*(j-0.5)/count` angular grid represented as
  `index+0.5` for zero-based C++ indices, `findReq()` bisection reuse,
  Cartesian x/y/z placement, zero velocity columns, circular-orbit metadata
  columns, and bisection iteration count. Remaining C++ gaps now include
  interpolation-grid disk caching if required for parity, full orbit-start
  boundary search/state-array generation, and full orbit-engine wiring.
- Documented the Fortran `make_startpoints()` irregular-energy noreg behavior
  as a later analysis item in `aidocs/cpp_orblib_port_plan.md` and
  `aidocs/KNOWLEDGE.md`. The code comment and local variable imply a "last
  irregular energy" rule, but the active Fortran condition is
  `maxval(irregular(:)) .eq. i`; because `irregular` is a 0/1 flag vector,
  this flags energy index 1 whenever any irregular energy exists. The C++
  port intentionally preserves this behavior for current parity.

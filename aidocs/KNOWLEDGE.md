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

- `origin`: `git@github.com:reinhardullrich/dynamite.git`
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
- `aidocs/cpp_orblib_port_plan.md`: branch-specific plan for the
  `fortran-to-cpp` experiment. It records the required priority order
  of correctness first and speed second, the DOP853 policy, allocation and
  hot-path rules, fixture-based acceptance criteria, C++ shared-library shape,
  and benchmark policy.
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
- `orblib_cpp/`: experimental C++ orbit-library backend on the
  `fortran-to-cpp` branch. The current branch builds
  `orblib_cpp/build/lib/liborblib_cpp.so`, exports ABI version `1`, and exposes
  generation entry-point stubs that return status `-100` until the C++ orbit
  engine is ported. The first ported numerical kernels are the C++ `Ran1`
  implementation in `orblib_cpp/include/ran1.hpp` and
  `orblib_cpp/source/ran1.cpp`, plus a translated DOP853 solver in
  `orblib_cpp/include/dop853.hpp` and `orblib_cpp/source/dop853.cpp`, a
  tightened C++ Carlson/Legendre elliptic-integral implementation in
  `orblib_cpp/include/elliptic_integrals.hpp` and
  `orblib_cpp/source/elliptic_integrals.cpp`, and the non-bar triaxial MGE
  setup/deprojection stage in `orblib_cpp/include/triaxial_mge.hpp` and
  `orblib_cpp/source/triaxial_mge.cpp`. It also includes
  `orblib_cpp/include/potential.hpp` and `orblib_cpp/source/potential.cpp` for
  the current C++ potential stack: stellar triaxial MGE potential/acceleration,
  the Plummer-style black-hole term, and dark-halo profiles 0 through 3 plus 5
  (`no halo`, NFW, Hernquist, triaxial cored logarithmic, and gNFW). It also
  includes `orblib_cpp/include/interpolated_potential.hpp` and
  `orblib_cpp/source/interpolated_potential.cpp` for an in-memory port of
  `interpolpotent.f90`'s acceleration interpolation math. The C++ orbit RHS
  formula lives in `orblib_cpp/include/orbit_rhs.hpp` and
  `orblib_cpp/source/orbit_rhs.cpp`, covering both non-rotating and
  barred-frame `Omega` terms from `orblib_f_new_mirror.f90`'s `derivs`.
  `orblib_cpp/include/orbit_integrator.hpp` and
  `orblib_cpp/source/orbit_integrator.cpp` wire the C++ DOP853 solver to that
  orbit RHS for single-orbit final-state integration and prescribed
  dense-output sample extraction. `orblib_cpp/include/orbit_classification.hpp`
  and `orblib_cpp/source/orbit_classification.cpp` port the Fortran
  angular-momentum sign-crossing orbit classification and moment formulas.
  `orblib_cpp/include/orbit_projection.hpp` and
  `orblib_cpp/source/orbit_projection.cpp` port the Fortran per-symmetry orbit
  projection and LOS-velocity formulas for non-rotating and rotating-frame
  sign tables. `orblib_cpp/include/orbit_psf.hpp` and
  `orblib_cpp/source/orbit_psf.cpp` port the Fortran PSF Gaussian convolution
  paths, including the single-Gaussian, tiny-sigma copy-through, and weighted
  MGE-PSF sigma-map branches. `orblib_cpp/include/orbit_aperture.hpp` and
  `orblib_cpp/source/orbit_aperture.cpp` port the Fortran boxed-aperture pixel
  lookup formula from `aperture_boxed_find()`.
  `orblib_cpp/include/orbit_histogram.hpp` and
  `orblib_cpp/source/orbit_histogram.cpp` port the Fortran LOSVD velocity bin
  mapping, per-aperture histogram accumulation, bin-order collapse,
  normalization, and sparse row-range formulas from `histogram_velbin()`,
  `histogram_store()`, `binning_add_it_up()`, and
  `histogram_write_compat_sparse()`.
  `Ran1` is tested against the existing Python/Fortran reference
  sequence; DOP853 is tested through the shared library on harmonic-oscillator
  final-state and dense-output samples; elliptic integrals are tested against
  SciPy; MGE setup, potential-stack evaluation, interpolation-grid evaluation,
  orbit RHS evaluation, single-orbit DOP853 final-state integration, and
  single-orbit dense-output sampling are tested against independent
  NumPy/SciPy implementations of the Fortran formulas. Orbit classification is
  tested against a Python mirror of the Fortran type and moment formulas, and
  projection is tested against a Python mirror of the Fortran `project_n()`
  formulas. PSF convolution is tested against a Python mirror of the Fortran
  single-precision Gaussian and sigma-map formulas. Boxed aperture mapping is
  tested against a Python mirror of the Fortran strict-bound and 1-based pixel
  flattening formula. LOSVD velocity-bin mapping and histogram accumulation
  are tested against Python mirrors of the Fortran clamp, strict-bound, zero
  aperture-pixel, and normalization-counter behavior. LOSVD bin-order
  collapse, normalization, and sparse row-range preparation are tested against
  Python mirrors of the Fortran writer-preparation formulas.
- `dynamite/orblib_api.py`: Python-facing orbit-library API facade. It provides
  typed request/result objects, `run_orbit_library()`, the active
  `fortran_shared_library` backend, and the experimental `cpp_shared_library`
  backend. The Fortran backend calls
  `orblib_fortran/build/lib/liborblib_fortran.so` through `ctypes`; the C++
  backend calls `orblib_cpp/build/lib/liborblib_cpp.so`. Python
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

- Python audit: found packaging, dependency, runtime-validation,
  orbit-library failure-detection, and dark-halo method risks.
- Fortran audit: found legacy failure-handling, solver-status, build-system,
  and uninitialized-data risks.
- Scientific audit: found the core non-rotating triaxial
  Schwarzschild/MGE modelling chain scientifically grounded, with caveats
  around convergence, barred-model benchmarking, cored-log halo density
  domains, and modelling priors.
- Full 2026-06-01 audit: this is now an adapted historical audit baseline. The
  original run found CI coverage gaps, unsafe output-state mutation, weak
  Python-to-Fortran failure detection, solver-result validation gaps, physical
  parameter domain gaps, and non-atomic model/cache writes. After the local
  Fortran cleanup, active orbit generation uses the direct shared-library API,
  active pytest coverage lives under `tests/`, and Python `NNLS` is the active
  weight-solver path.
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
- C++ orbit-library port experiment: branch `fortran-to-cpp` exists for a
  future C++ replacement of the active Fortran orbit-library backend. The port
  must use the current Fortran shared-library backend and fixtures as the
  numerical oracle. Correctness is the first rule; among correct versions,
  optimize aggressively for speed, allocation behavior, RHS/acceleration
  throughput, cache locality, and reproducible parallel execution. The current
  implementation slices build a C++ shared library and wire
  `cpp_shared_library` into Python with a hard not-implemented status for
  generation calls. The first actual ported Fortran kernels are `ran1_nr.f`,
  implemented as a no-hot-loop-allocation C++ `Ran1` class with ABI test helper
  `orblib_cpp_api_ran1_sequence`, and `numerics/dop853.f`, implemented as a
  reusable C++ `Dop853` solver with preallocated work arrays, dense-output
  evaluation, Fortran-style result counters, and ABI test helper
  `orblib_cpp_api_dop853_harmonic`. The current branch also has C++ support for
  `numerics/ellipint.f90` and the non-bar `tp_setup()`/`iniparam_from_arrays()`
  MGE setup formulas, plus stellar triaxial MGE potential/acceleration
  evaluation across the inner approximation, mid-radius quadrature, and
  far-field point-mass approximation. The branch now also ports the
  Plummer-style black-hole term, dark-halo profiles 0 through 3 plus profile 5
  gNFW with its beta-function helper stack, and the in-memory acceleration
  interpolation-grid math from `interpolpotent.f90`,
  plus the orbit RHS derivative formula for non-rotating and `Omega != 0`
  barred-frame integration, and a single-orbit DOP853 final-state integration
  helper with prescribed dense-output sample extraction using that RHS, plus
  the orbit classification, moment, projection, LOS-velocity, PSF convolution,
  boxed-aperture pixel lookup, LOSVD velocity-bin mapping, per-aperture
  histogram accumulation, bin-order collapse, normalization, and sparse
  row-range formulas. The legacy `interpolgrid` disk-cache contract,
  orbit-start generation, qgrid accumulation, full orbit-engine wiring, and
  binary output writing are the next unported dependencies.

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
- `pip check` passed after the local editable install.
- GNU Fortran 13.3.0 at `/usr/bin/gfortran` was used for the active
  no-GALAHAD Fortran build.
- `orblib_fortran/Makefile` and `orblib_fortran/Makefile.linux` treat the
  shared library as the only supported runtime build product. `make`,
  `make all`, `make nogal`, and `make shared` build
  `orblib_fortran/build/lib/liborblib_fortran.so`; temporary object/module
  directories may exist during compilation but are generated artifacts.
- `orblib_cpp/Makefile` builds the experimental C++ shared library with
  `make -C orblib_cpp shared`; generated C++ build output lives under ignored
  `orblib_cpp/build/`.
- Use `MPLCONFIGDIR=/tmp/dynamite-mplconfig` for local/headless Matplotlib
  commands to avoid config-cache warnings.
- For future fresh setup, `uv` is acceptable and likely faster, but the current
  completed audit install used `.venv` plus `pip`.

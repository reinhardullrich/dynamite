# C++ Orblib Port Plan

Date: 2026-06-02

Branch: `fortran-to-cpp`

Scope: port the active orbit-library Fortran backend to C++ while preserving
the active Python-facing orbit-library API semantics. This plan covers active
code under `orblib_fortran/source/`, especially orbit-start generation,
potential/interpolation evaluation, DOP853 orbit integration, orbit
classification, projection, PSF convolution, aperture mapping, LOSVD binning,
intrinsic moment grids, and binary orbit-library output.

Archived solver code, archived development tests, and archived particle export
utilities are not part of this port.

## Non-Negotiable Rules

1. Correctness comes first.
2. Among implementations that are correct, make the code as fast as practical.
3. The current Fortran shared-library backend is the numerical oracle until the
   C++ backend proves parity.
4. Do not silently change numerical methods, precision contracts, random
   sampling, dense-output sampling, binary output layout, or cache behavior.
5. Any deliberate numerical deviation must be isolated, benchmarked, documented,
   and approved before it becomes the default.

The goal is not "nice C++" at the cost of performance. The goal is a correct,
maintainable, high-throughput compiled backend.

## Acceptance Fixtures

The C++ backend must be tested against existing Fortran-derived fixtures:

- `tests/fixtures/orblib_losvd/data/comparison_losvd_shared_library.npz`
  is the current direct shared-library fixture and should be the tight parity
  target where deterministic behavior is expected.
- `tests/fixtures/orblib_losvd/data/comparison_losvd.npz` is the historical
  executable-generated fixture and remains a compatibility reference with its
  separate tolerance policy.
- `tests/test_fortran_orblib_output.py` defines the slow generated LOSVD
  workflow that the C++ backend should eventually mirror.
- `tests/test_orblib_api.py` defines the Python API facade behavior that the
  C++ backend should match.

Initial C++ tests should add small, deterministic unit fixtures before running
the full LOSVD workflow:

- `ran1_nr.f` random-number parity;
- DOP853 integration on simple known ODEs;
- DOP853 dense-output interpolation at prescribed sample times;
- potential/acceleration parity for selected MGE and dark-halo inputs;
- orbit-start array parity;
- one-orbit classification/projection/histogram parity;
- full small NGC6278 LOSVD parity.

## Proposed Backend Shape

Add a new backend without removing the Fortran backend:

```text
orblib_cpp/
  include/
  source/
  build/lib/liborblib_cpp.so
```

Expose a C ABI from C++ so Python can call it through `ctypes` in the same
style as the current Fortran shared library:

```text
orblib_cpp_api_abi_version
orblib_cpp_api_ran1_sequence
orblib_cpp_api_elliptic_legendre
orblib_cpp_api_triaxial_mge_setup
orblib_cpp_api_triaxial_mge_evaluate
orblib_cpp_api_potential_stack_evaluate
orblib_cpp_api_interpolated_potential_evaluate
orblib_cpp_api_orbit_rhs_evaluate
orblib_cpp_api_classify_orbit_samples
orblib_cpp_api_project_orbit_samples
orblib_cpp_api_apply_psf
orblib_cpp_api_find_boxed_aperture_pixels
orblib_cpp_api_losvd_velocity_bins
orblib_cpp_api_accumulate_losvd_histogram
orblib_cpp_api_collapse_losvd_binning
orblib_cpp_api_normalize_losvd_histogram
orblib_cpp_api_sparse_losvd_ranges
orblib_cpp_api_qgrid_boundaries
orblib_cpp_api_accumulate_qgrid
orblib_cpp_api_normalize_qgrid
orblib_cpp_api_write_qgrid_file
orblib_cpp_api_write_losvd_histogram_file
orblib_cpp_api_write_population_mass_file
orblib_cpp_api_write_orbit_class_file
orblib_cpp_api_orbitstart_calc_start_state
orblib_cpp_api_orbitstart_find_equivalent_radius
orblib_cpp_api_integrate_orbit_final_state
orblib_cpp_api_integrate_orbit_samples
orblib_cpp_api_dop853_harmonic
orblib_cpp_api_run_orbitstart_memory
orblib_cpp_api_run_orblib_direct
```

Python should gain a separate backend name, for example
`cpp_shared_library`. The current `fortran_shared_library` backend should stay
the default until C++ parity and performance are proven.

Current branch status:

- C++ shared-library skeleton, ABI version, and Python backend selection are in
  place.
- `ran1_nr.f` is ported as `dynamite::orblib_cpp::Ran1` and tested against the
  existing Python/Fortran reference sequence.
- `numerics/dop853.f` is ported as `dynamite::orblib_cpp::Dop853`, including
  adaptive stepping and dense-output evaluation. The current test fixture
  validates a harmonic oscillator final state and dense samples through the
  shared library.
- `numerics/ellipint.f90` is ported as C++ Carlson/Legendre elliptic
  integrals. The formulas are preserved, with a tighter convergence threshold
  than the original Fortran because the original setup-only routine differs
  from SciPy by roughly `1e-8` for larger modulus cases.
- The non-bar `iniparam_from_arrays()` plus `tp_setup()` MGE setup/deprojection
  stage is ported as `dynamite::orblib_cpp::TriaxialMgeSetup` and tested
  against an independent NumPy implementation of the Fortran formulas on the
  NGC6278 fixture MGE.
- Stellar triaxial MGE potential/acceleration evaluation is ported for the
  inner approximation, mid-radius quadrature, and outer point-mass branches,
  and is tested against independent Python/SciPy calculations of the Fortran
  formulas.
- The current `dmpotent.f90` black-hole/dark-halo additions are ported for the
  Plummer-style black-hole term, dark-halo profiles 0 through 3, and profile 5
  gNFW: no halo, NFW, Hernquist, triaxial cored logarithmic, and gNFW. The
  profile 5 path includes the unregularized incomplete-beta helper stack from
  `orblib_fortran/source/numerics/specfunc_beta.f90`. The combined
  potential-stack ABI helper is tested against independent Python/SciPy
  calculations of the Fortran formulas.
- The in-memory `interpolpotent.f90` acceleration interpolation math is ported
  as `dynamite::orblib_cpp::InterpolatedPotential`, including the radius range
  formulas, spherical-octant grid, log-acceleration storage, trilinear
  interpolation, and direct fallback outside the grid. The legacy
  `interpolgrid` disk-cache read/write behavior is not implemented yet.
- The orbit RHS formula from `orblib_f_new_mirror.f90`'s `derivs` is ported as
  `dynamite::orblib_cpp::evaluate_orbit_rhs`, including both the non-rotating
  derivative assignment and the barred-frame `Omega` terms. It is tested
  against independent Python calculations of the Fortran formulas.
- Single-orbit final-state DOP853 integration using the orbit RHS is ported as
  `dynamite::orblib_cpp::integrate_orbit_final_state` and tested against SciPy
  DOP853 on an independent softened black-hole RHS.
- Prescribed dense-output sample extraction for a single orbit is ported as
  `dynamite::orblib_cpp::integrate_orbit_samples` and tested against SciPy
  DOP853 dense output on the same independent softened black-hole RHS.
- Orbit classification and moment calculation are ported as
  `dynamite::orblib_cpp::classify_orbit_samples` and tested against a Python
  mirror of the Fortran `integrator_find_orbtype()` formulas for all five orbit
  classes.
- Per-symmetry projection and LOS-velocity calculation are ported as
  `dynamite::orblib_cpp::project_orbit_samples` and tested against a Python
  mirror of the Fortran `project_n()` formulas for all five orbit types, all
  eight projection symmetries, and non-rotating/rotating-frame sign tables.
- PSF Gaussian convolution is ported as
  `dynamite::orblib_cpp::apply_psf_to_projected_samples` and tested against a
  Python mirror of the Fortran `psf_gaussian()` and `psf_sigma_map()` formulas
  for tiny single-Gaussian copy-through, resolved single-Gaussian convolution,
  and weighted MGE-PSF convolution.
  Histograms, qgrid accumulation, and output writing are not part of these
  helpers.
- Boxed aperture pixel lookup is ported as
  `dynamite::orblib_cpp::find_boxed_aperture_pixels` and tested against a
  Python mirror of the Fortran `aperture_boxed_find()` formula, including
  conversion-factor scaling, strict boundaries, and 1-based flattened pixel
  IDs.
- LOSVD velocity-bin mapping and per-aperture histogram accumulation are
  ported as `dynamite::orblib_cpp::map_losvd_velocity_bins` and
  `dynamite::orblib_cpp::accumulate_losvd_histogram`, and tested against
  Python mirrors of the Fortran `histogram_velbin()` and `histogram_store()`
  formulas.
- LOSVD bin-order collapse, normalization, and sparse row-range preparation are
  ported as `dynamite::orblib_cpp::collapse_losvd_binning`,
  `dynamite::orblib_cpp::normalize_losvd_histogram`, and
  `dynamite::orblib_cpp::compute_sparse_losvd_ranges`, and tested against
  Python mirrors of the Fortran `binning_add_it_up()`, `histogram_write()`,
  and `histogram_write_compat_sparse()` preparation formulas. Sparse LOSVD
  Fortran-record binary serialization is ported in
  `orblib_cpp/source/orbit_output.cpp` as `write_losvd_histogram_file()` and
  tested by reading the generated file through SciPy `FortranFile`. Full
  orbit-engine wiring is not part of this helper.
- Intrinsic qgrid boundary setup, moment accumulation, orbit-type channel
  accumulation, and normalization are ported in `orblib_cpp/source/orbit_qgrid.cpp`
  and tested against Python mirrors of the Fortran `qgrid_setup()`,
  `qgrid_store()`, and `qgrid_write()` memory-side formulas for both
  non-rotating and rotating-frame sign-table paths.
- Qgrid Fortran-record binary serialization is ported in
  `orblib_cpp/source/orbit_output.cpp` as `write_qgrid_file()` and tested by
  writing a C++ `*_qgrid.dat` file that SciPy `FortranFile` reads back with
  the existing Python reader's record order.
- Population projected-mass Fortran-record binary serialization is ported in
  `orblib_cpp/source/orbit_output.cpp` as `write_population_mass_file()` and
  tested by reading generated `*_pops.dat` records through SciPy
  `FortranFile`.
- Formatted orbit-class output is ported in
  `orblib_cpp/source/orbit_output.cpp` as `write_orbit_class_file()` and
  tested against the current Python reader's `reshape(..., order='F')`
  contract.
- Direct-potential orbit-start kernels `calc_startpos()` and `findReq()` are
  ported in `orblib_cpp/source/orbit_start.cpp` as
  `calculate_orbit_start_state()` and `find_equivalent_radius()`, and tested
  against independent Python mirrors of the Fortran state construction,
  negative-kinetic-energy fallback, bisection range, and `1e-7` relative
  potential stopping rule.
- The pure orbit-start scheduling loops `find_unregorbits()` and the
  radius/noreg part of `make_startpoints()` are ported as
  `compute_unregularized_orbit_grid()` and `compute_tube_start_schedule()`,
  with ABI tests for the reverse `nI2` propagation scan, irregular-energy
  boundary replacement, nearly closed-boundary radius formula, and the exact
  Fortran `maxval(irregular) == i` flag condition.
- The per-record `make_boxstartpoints()` angular-grid and record construction
  path is ported as `calculate_box_start_record()`, reusing
  `find_equivalent_radius()` and testing the Fortran one-based
  `Pi/2*(j-0.5)/count` angle formula, represented as `index+0.5` for
  zero-based C++ indices, plus Cartesian placement, zero velocity fields,
  circular-orbit metadata fields, and bisection iteration count.
- The orbit-specific C++ engine is still not implemented yet:
  interpolation-grid disk caching, orbit-start boundary search/full begin-state
  generation, full orbit-engine wiring, and full-output orchestration still
  remain.

## Known Fortran Parity Notes To Revisit

- `orbitstart_f.f90`'s `make_startpoints()` has an apparent intent/code
  mismatch in the noreg flag for irregular energies. The local variable is
  named `LastIrregE`, and the nearby comment says "if this is the last
  irregular energy do not regularize", but the active condition is
  `if (maxval(irregular(:)) .eq. i) noreg = 1`. Because `irregular` is a
  0/1 flag vector, this condition flags energy index `i == 1` whenever any
  energy is irregular, rather than flagging the last irregular energy. The C++
  port currently preserves this exact behavior for parity and tests it
  explicitly. This should be analyzed later before any intentional cleanup or
  scientific behavior change.

## DOP853 Policy

The active Fortran backend uses DOP853, an explicit Runge-Kutta method of order
`8(5,3)` with stepsize control and dense output. DYNAMITE depends on dense
output through the current `SOLOUT`/`CONTD8` path to sample positions and
velocities at controlled output times.

Do not replace this with Boost `runge_kutta_dopri5`; that is a different
method.

Allowed starting points:

- use Hairer's C DOP853 as a reference or source after checking redistribution
  terms;
- conservatively port the current DOP853 implementation to C++;
- implement DOP853 from coefficients and formulas only if tests first lock down
  the exact behavior expected by this backend.

The C++ DOP853 implementation must preserve:

- scalar tolerance mode used by the current code;
- initial step-size reuse behavior equivalent to current `WORK(7)`;
- maximum-step/error-failure behavior;
- dense output for all 6 orbit state components;
- sample-time offset behavior currently driven by `ran1`;
- energy-conservation retry policy;
- diagnostic counters needed for debugging and benchmarks.

## Hot-Path Performance Rules

Avoid allocation in hot loops. In particular, do not allocate heap memory inside:

- the DOP853 step loop;
- derivative/RHS evaluation;
- dense-output sample extraction;
- per-sample projection;
- PSF convolution inner loops;
- aperture lookup;
- LOSVD histogram binning;
- per-orbit qgrid/moment accumulation.

Use reusable workspace objects allocated at setup time or per worker:

- DOP853 work arrays;
- state and derivative arrays;
- dense-output coefficients;
- sampled positions and velocities;
- projected coordinates and line-of-sight velocities;
- histogram scratch;
- qgrid/moment scratch;
- orbit-classification scratch.

Prefer:

- `std::array<double, 6>` for fixed orbit state vectors;
- contiguous `std::vector<double>` buffers with explicit `resize` during setup;
- `std::span` or raw pointer plus size in hot functions;
- precomputed dimensions and strides;
- `reserve()` before filling variable-length vectors;
- explicit status codes at ABI boundaries.

Avoid in hot paths unless a benchmark proves no cost:

- `std::function`;
- virtual dispatch;
- repeated `new`/`delete`;
- repeated `std::vector` growth;
- exceptions crossing ABI boundaries;
- string formatting or logging per orbit sample;
- bounds-checked containers in inner loops.

## RHS And Potential Evaluation

The derivative function is one of the most important hot paths. Each DOP853
orbit integration calls it many times. The C++ RHS implementation should be
optimized deliberately:

- keep model/potential data in a compact context object;
- pass the context by pointer/reference, not by copying;
- make the acceleration evaluator inlineable where possible;
- precompute constants and interpolation tables before orbit loops;
- avoid callback chains that bounce between C++ and Fortran;
- separate non-rotating and rotating-frame cases so the common case does not
  pay unnecessary branch cost inside every evaluation if avoidable;
- measure acceleration evaluation time separately from the DOP853 controller.

If a generic callback interface is needed for tests, keep it outside the main
production hot loop or provide a templated/static-polymorphism path for the
real backend.

## Parallelism

The natural parallel unit is an orbit-library task or a batch of orbit bundles,
not an individual DOP853 stage. Keep the first C++ backend compatible with the
current Python process-level orchestration, then benchmark whether C++ internal
threading helps.

Rules:

- no global mutable numerical state in the C++ backend;
- each worker owns its scratch buffers;
- random-state behavior must be reproducible;
- binary output writing must remain deterministic and serialized or otherwise
  explicitly ordered;
- avoid oversubscription between Python process pools and C++ thread pools.

## Binary Output Contract

The first C++ backend should write the same binary `datfil/` output contract
that Python already reads:

- qgrid files;
- LOSVD histogram files;
- orbit-classification output;
- `tube_done`, `box_done`, and `orblib_done` markers.

Changing output to a memory-only API is a separate refactor. It should not be
mixed with the first C++ parity port.

## Implementation Order

1. Done: add the C++ backend skeleton, build target, and ABI version function.
2. Done: add Python backend selection for `cpp_shared_library` without changing the
   default backend.
3. Done: port `ran1_nr.f` and test against the Python/Fortran reference
   sequence.
4. Done: port DOP853 and test dense output on a harmonic-oscillator ODE
   fixture. The branch also has a single-orbit final-state integration helper
   using the C++ orbit RHS.
5. In progress: port potential and acceleration evaluation. Done so far:
   elliptic setup helpers, non-bar triaxial MGE setup/deprojection, stellar
   triaxial MGE potential/acceleration evaluation, Plummer-style black-hole
   contribution, dark-halo profiles 0 through 3 plus profile 5 gNFW, and
   in-memory acceleration interpolation-grid math, the orbit RHS formula, and
   single-orbit DOP853 final-state integration plus prescribed dense-output
   sample extraction using that RHS, plus orbit classification, moment
   calculation, projection, LOS-velocity calculation, PSF convolution, and
   boxed aperture mapping, plus LOSVD velocity-bin mapping and per-aperture
   histogram accumulation, bin-order collapse, normalization, and sparse
   row-range preparation, plus intrinsic qgrid boundary setup, accumulation,
   and normalization, plus qgrid and LOSVD sparse Fortran-record file
   serialization, plus population-mass binary serialization and formatted
   orbclass output writing, plus direct-potential orbit-start state
   construction and equivalent-radius bisection. Still required: legacy
   interpolation-grid disk caching if C++ parity requires it, full orbit-start
   boundary search/array generation, full-output orchestration, and
   Fortran-value parity tests for full orbit integration.
6. Port orbit-start generation; test against current begin/beginbox fixtures.
   Direct-potential `calc_startpos()` and `findReq()` kernels are done; inner
   boundary, outer boundary, tube-width, orbit-type probing, box startpoint,
   and full begin/beginbox array generation still remain.
7. Port one-orbit integration and classification; test against Fortran.
   Single-orbit final-state integration, dense sample extraction, and the
   standalone classification/moment kernel are done; full one-orbit parity
   still needs the Fortran sampling schedule and downstream wiring.
8. Port aperture, histogram, qgrid, and output writing.
   Per-symmetry projection, LOS velocity, PSF convolution, and boxed aperture
   mapping are done, and the LOSVD velocity-bin plus per-aperture histogram
   accumulation core plus memory-side sparse row preparation are done; qgrid
   memory-side accumulation is done; qgrid and LOSVD sparse file serialization
   are done; population-mass and orbclass output writing are done; full engine
   orchestration still remains.
9. Run full generated LOSVD parity against
   `comparison_losvd_shared_library.npz`.
10. Only after correctness, benchmark and optimize memory layout, branching,
   allocation, parallelism, and compiler flags.

## Benchmark Policy

Every performance claim must include:

- compiler and flags;
- CPU/thread count;
- backend name and ABI version;
- orbit grid size and fixture name;
- wall time split by stage;
- number of derivative evaluations;
- accepted/rejected DOP853 step counts;
- output byte counts;
- max absolute and relative output differences versus Fortran.

Correctness failures invalidate speed comparisons. The fastest wrong backend is
not useful.

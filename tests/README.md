# DYNAMITE Orblib Backend And API Tests

This test tree is the local correctness baseline for the active orblib Fortran
shared-library backend, the experimental C++ backend, the Python direct-input
API facade, and future replacement work.

Default run:

```bash
.venv/bin/python -m pytest tests
```

The default suite runs fast fixture checks and small Fortran kernel parity
tests if `gfortran` is available. Slow model-generation tests are skipped by
default.

Opt-in checks:

```bash
make -C orblib_fortran shared
DYNAMITE_RUN_ORBLIB_FORTRAN_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_inventory.py
DYNAMITE_RUN_SLOW_TESTS=1 DYNAMITE_RUN_ORBLIB_FORTRAN_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_orblib_output.py
DYNAMITE_RUN_SLOW_TESTS=1 DYNAMITE_RUN_ORBLIB_FORTRAN_TESTS=1 .venv/bin/python -m pytest tests
make -C orblib_cpp shared
DYNAMITE_RUN_ORBLIB_CPP_TESTS=1 .venv/bin/python -m pytest tests/test_cpp_inventory.py tests/test_orblib_api.py -m orblib_cpp
```

Current coverage:

- embedded LOSVD, chi-square, and random-number values extracted from the
  historical example fixtures;
- Python `MyRand` against the saved legacy random sequence;
- compiled Fortran `ran1_nr.f` against Python `MyRand`;
- compiled archived Fortran `nnls95.f` against `scipy.optimize.nnls` for
  several reference NNLS cases;
- fast unit coverage for the Python-facing direct-input shared-library
  orbit-library API facade;
- inventory and ABI coverage for the experimental C++ shared-library backend;
- C++ `Ran1` random-number kernel parity against the Python/Fortran reference
  sequence;
- C++ DOP853 harmonic-oscillator final-state and dense-output validation
  through the experimental shared library;
- C++ elliptic-integral validation against SciPy and C++ non-bar triaxial MGE
  setup/deprojection validation against the Fortran formulas;
- C++ stellar triaxial MGE potential/acceleration validation across inner,
  mid-radius quadrature, and far-field branches;
- C++ combined potential-stack validation for the Plummer-style black-hole
  term and supported dark-halo profiles 0 through 3 plus profile 5 gNFW
  against independent Python/SciPy calculations of the Fortran formulas;
- C++ in-memory acceleration interpolation-grid validation against an
  independent Python implementation of the Fortran `interpolpotent.f90`
  metadata, log-acceleration grid, trilinear interpolation, and direct-fallback
  formulas;
- C++ orbit RHS validation for the non-rotating and barred-frame `Omega`
  branches against independent Python calculations of the Fortran `derivs`
  formulas;
- C++ single-orbit final-state DOP853 integration validation against SciPy
  DOP853 on an independent softened black-hole RHS;
- C++ single-orbit dense-output sample validation against SciPy DOP853 dense
  output on the same independent softened black-hole RHS;
- C++ orbit classification and moment validation against a Python mirror of
  the Fortran `integrator_find_orbtype()` formulas for all five orbit classes;
- C++ projection and LOS-velocity validation against a Python mirror of the
  Fortran `project_n()` formulas across all orbit types, all eight projection
  symmetries, and non-rotating/rotating-frame sign tables;
- C++ PSF Gaussian convolution validation against a Python mirror of the
  Fortran `psf_gaussian()` and `psf_sigma_map()` branches;
- C++ boxed aperture pixel-mapping validation against a Python mirror of the
  Fortran `aperture_boxed_find()` strict-bound and 1-based flattening formula;
- C++ LOSVD velocity-bin and histogram accumulation validation against Python
  mirrors of the Fortran `histogram_velbin()` and `histogram_store()` formulas;
- C++ LOSVD bin-order collapse, normalization, and sparse row-range validation
  against Python mirrors of the Fortran writer-preparation formulas;
- C++ sparse LOSVD Fortran-record file serialization validation by reading the
  generated file through SciPy `FortranFile`;
- C++ intrinsic qgrid boundary, accumulation, and normalization validation
  against a Python mirror of the Fortran `qgrid_*` formulas;
- C++ qgrid Fortran-record file serialization validation by reading the
  generated file through SciPy `FortranFile`;
- C++ population-mass Fortran-record file serialization validation through
  SciPy `FortranFile`;
- C++ formatted orbclass output validation against the current Python
  `reshape(..., order='F')` reader contract;
- C++ orbit-start `calc_startpos()` and `findReq()` kernel validation against
  independent Python mirrors of the Fortran formulas, plus unregularized-grid
  and tube-start radius/noreg schedule validation against Python mirrors of
  the Fortran loop order and flag rules;
- validation that the experimental C++ generation entry points fail with the
  explicit not-implemented status until the orbit engine is ported;
- fast coverage for the direct-input orbit-start and full orbit-library
  payload extraction, plus opt-in coverage for the non-bar direct-input
  shared-library orbit-start ABI;
- inventory of orblib Fortran shared-library sources used by the Python
  runtime;
- inventory checks that NNLS/GALAHAD Fortran and legacy `triaxmass*` mass
  helpers are archived, not active;
- validation that current configs reject archived `LegacyWeightSolver`;
- static coverage for the historical Python examples, shell examples, and
  YAML/notebook workflow intent by embedding the relevant code/config facts
  directly in pytest;
- validation of current tutorial configs and notebooks that still live under
  `docs/`;
- no dependency on external historical test folders for the default suite;
- an opt-in slow orblib Fortran orbit-library output comparison that
  regenerates the NGC6278 LOSVD workflow once, compares it against the
  historical executable-generated `comparison_losvd.npz` with legacy
  compatibility tolerances, and compares it against
  `comparison_losvd_shared_library.npz` with full-array `1e-12` tolerance.

The slow marker is used for integration tests that generate orbit libraries and
model outputs.

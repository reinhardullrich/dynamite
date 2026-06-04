# DYNAMITE Orblib Fortran And API Tests

This test tree is the local correctness baseline for the active orblib Fortran
shared-library backend, the Python direct-input API facade, and any future
replacement work.

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
```

Current coverage:

- embedded LOSVD, chi-square, and random-number values extracted from the
  historical example fixtures;
- Python `MyRand` against the saved legacy random sequence;
- compiled Fortran `ran1_nr.f90` against Python `MyRand`;
- compiled archived Fortran `nnls95.f` against `scipy.optimize.nnls` for
  several reference NNLS cases;
- fast unit coverage for the Python-facing direct-input shared-library
  orbit-library API facade;
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

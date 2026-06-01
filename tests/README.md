# DYNAMITE Fortran Replacement Tests

This test tree is for building a correctness baseline before replacing orblib
Fortran code with Python implementations.

Default run:

```bash
.venv/bin/python -m pytest tests
```

The default suite runs fast fixture checks and small Fortran kernel parity
tests if `gfortran` is available. Slow model-generation tests are skipped by
default.

Opt-in checks:

```bash
DYNAMITE_RUN_ORBLIB_FORTRAN_EXEC_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_inventory.py
DYNAMITE_RUN_SLOW_TESTS=1 DYNAMITE_RUN_ORBLIB_FORTRAN_EXEC_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_orblib_output.py
DYNAMITE_RUN_SLOW_TESTS=1 DYNAMITE_RUN_ORBLIB_FORTRAN_EXEC_TESTS=1 .venv/bin/python -m pytest tests
```

Current coverage:

- embedded LOSVD, chi-square, and random-number values extracted from the
  historical example fixtures;
- Python `MyRand` against the saved legacy random sequence;
- compiled Fortran `ran1_nr.f` against Python `MyRand`;
- compiled archived Fortran `nnls95.f` against `scipy.optimize.nnls` for
  several reference NNLS cases;
- inventory of orblib Fortran executables used by the Python runtime;
- an inventory check that NNLS/GALAHAD Fortran is archived, not active;
- static coverage for the historical Python examples, shell examples, and
  YAML/notebook workflow intent by embedding the relevant code/config facts
  directly in pytest;
- validation of current tutorial configs and notebooks that still live under
  `docs/`;
- no dependency on external historical test folders for the default suite;
- an opt-in slow orblib Fortran orbit-library output comparison that
  regenerates the historical NGC6278 LOSVD workflow and compares the produced
  velocity grid and LOSVD array statistics against `comparison_losvd.npz`.

The slow marker is used for integration tests that generate orbit libraries and
model outputs.

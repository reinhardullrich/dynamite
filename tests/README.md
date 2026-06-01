# DYNAMITE Fortran Replacement Tests

This test tree is for building a correctness baseline before replacing legacy
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
DYNAMITE_RUN_LEGACY_EXEC_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_inventory.py
DYNAMITE_RUN_SLOW_TESTS=1 .venv/bin/python -m pytest tests/test_existing_dev_workflows.py
DYNAMITE_RUN_SLOW_TESTS=1 DYNAMITE_RUN_LEGACY_EXEC_TESTS=1 .venv/bin/python -m pytest tests
```

Current coverage:

- frozen LOSVD, chi-square, and random-number fixtures from `dev_tests/data`;
- Python `MyRand` against the saved legacy random sequence;
- compiled Fortran `ran1_nr.f` against Python `MyRand`;
- compiled Fortran `nnls95.f` against `scipy.optimize.nnls` for several
  reference NNLS cases;
- inventory of legacy Fortran executables used by the Python runtime;
- static coverage for all dev-test Python examples, shell examples, YAML
  configs, and tutorial notebooks found in the repository;
- opt-in smoke/parity wrappers around existing `dev_tests` workflows.

The slow tests are intentionally gated because they can generate orbit
libraries and model outputs.

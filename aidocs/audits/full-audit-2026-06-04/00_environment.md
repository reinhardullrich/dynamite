# 00 Environment

Audit date: 2026-06-04

## Local Install Policy

Development and audit dependencies are local to the repository in `.venv/`.
No global Python installation, system package installation, or `sudo` action is
required for the current audit baseline.

## Python Environment

Observed during this audit:

- Python: `.venv/bin/python`, Python 3.12.3.
- pytest: 9.0.3.
- `pip check`: passed.
- `compileall` over `dynamite` and `tests`: passed.

Observed warning:

- pip reports `/home/reinhard/.cache/pip` is not writable/owned by this user
  and disables its cache. This is operational noise, not a dependency failure.

## Fortran Environment

- Active build command: `make -C orblib_fortran shared`.
- Active build product:
  `orblib_fortran/build/lib/liborblib_fortran.so`.
- The makefile still uses aggressive local optimization flags including
  `-ffast-math` and `-march=native`.

Risk:

- `-march=native` reduces portability of locally built binaries.
- `-ffast-math` can change floating-point semantics; acceptable only if the
  scientific parity tests remain the acceptance gate.

## Verification Results

Commands run on 2026-06-04:

```bash
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q dynamite tests
make -C orblib_fortran shared
git diff --check
.venv/bin/python -m pytest
DYNAMITE_RUN_SLOW_TESTS=1 DYNAMITE_RUN_ORBLIB_FORTRAN_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_orblib_output.py tests/test_fortran_inventory.py
```

Results:

- `pip check`: no broken requirements.
- compile check: no output, success.
- Fortran shared build: success.
- diff whitespace check: success.
- default pytest: 62 passed, 6 skipped, 1 warning.
- opt-in slow Fortran/output tests: 11 passed, 1 warning.

## Environment Findings

### ENV-001 - Dependency versions are not locked

Severity: Medium.

The local `.venv/` works today, but dependency versions are not pinned by a
lockfile. Future audit runs may drift.

Recommendation: add a lock/snapshot mechanism for reproducible audit
environments, or at least record installed versions when publishing benchmark
numbers.

### ENV-002 - Headless Matplotlib config/cache path is not explicitly set

Severity: Low/Medium.

Earlier fixture generation emitted Matplotlib cache-directory warnings when the
home config directory was not writable. The current pytest run did not fail,
but local/headless runs should set a writable `MPLCONFIGDIR`.

Recommendation: document or set `MPLCONFIGDIR` in CI and long-running local
automation.

### ENV-003 - Fortran build flags are performance-oriented, not reproducibility-oriented

Severity: Medium.

The active makefiles still use `-ffast-math -O3 -march=native`. This is
reasonable for local performance benchmarking but not ideal for portable
scientific reproducibility.

Recommendation: add named build profiles: `debug`, `portable-release`, and
`native-fast`.

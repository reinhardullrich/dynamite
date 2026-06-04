# 01 Build Packaging

Audit date: 2026-06-04

## Current Build State

- Python package still uses `setup.py`; no `pyproject.toml` was observed.
- `setup.py` declares `python_requires=">=3.10"`.
- Local editable install in `.venv/` works.
- Active Fortran build is shared-library-only for current runtime use.
- `make -C orblib_fortran shared` passed.
- `.github/workflows/ci.yml` runs on Python 3.10, 3.11, and 3.12; builds the
  shared library; installs the package with testing extras; runs
  shared-library inventory tests; and runs default pytest.

## Findings

### BP-001 - Package dependency metadata is not enough for docs/tests/dev

Severity: Medium.

The local `.venv` can run tests, but CI and package metadata do not clearly
separate runtime, testing, documentation, and optional solver dependencies.

Recommendation: define explicit extras or requirements files for runtime,
testing, docs, optional CVXOPT, and local benchmark tooling.

### BP-002 - Build profiles are missing

Severity: Medium.

The current makefile supports the active shared-library product, but not named
scientific build profiles.

Recommendation: add explicit `debug`, `portable`, and `native-fast` profiles
with documented flags and expected numeric tolerance implications.

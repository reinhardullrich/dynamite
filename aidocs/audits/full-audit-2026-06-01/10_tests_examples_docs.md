# 10 Tests, Examples, CI, and Upstream Docs Audit

Current-status update, 2026-06-02: this chapter has been adapted for the
`fortran-cleanup` branch. Old development-test content is archived under
`archive/dev_tests/`; active local pytest coverage lives under `tests/`; and
the active Fortran inventory/build checks target the orblib shared library, not
executables.

Scope: `.github/workflows/ci.yml`, `setup.py`, `requirements.txt`, active
`tests/`, archived `archive/dev_tests/`, and upstream Sphinx/notebook
documentation under `docs/`.

This section records verification coverage. It does not modify upstream
Sphinx `docs/`.

## Commands/checks run

```bash
MPLCONFIGDIR=/tmp/dynamite-mplconfig .venv/bin/python -m pytest --collect-only -q dev_tests
```

Original result before cleanup: pytest collection of old `dev_tests` failed
before collecting any runnable tests.

Current result after cleanup: active local pytest coverage is under `tests/`;
focused fast tests and opt-in slow orblib shared-library parity tests passed
during the cleanup.

Errors:

- `archive/dev_tests/test_dataprep.py` imports missing
  `dynamite.data_prep.data_prep_test`.
- `archive/dev_tests/test_decomp.py` constructs a configuration at import time using
  the bare relative path `user_test_config_ml.yaml`, which fails from the repo
  root.

## Findings

### TED-001 - High - CI does not install the package from `setup.py`

Evidence:

- `.github/workflows/ci.yml:40-45` installs `requirements.txt` and installs the
  package only if `pyproject.toml` exists.
- This repository currently has `setup.py` but no `pyproject.toml`.
- `.github/workflows/ci.yml:58-63` sets `PYTHONPATH=.` for test execution.

Impact:

CI imports the source tree directly rather than testing the installed package.
That misses package-data behavior and packaging errors, especially around the
Fortran shared library listed in `setup.py`.

Recommended fix:

Install the package explicitly in CI:

```bash
python -m pip install -e ".[testing]"
```

or migrate packaging to `pyproject.toml` and keep CI aligned with it.

### TED-002 - High - CI does not run pytest

Evidence:

- `.github/workflows/ci.yml:61-63` originally commented out `pytest -v` and
  directly ran `archive/dev_tests/test_nnls.py`.

Impact:

Collection failures, import failures, and additional test scripts are invisible
to CI. The current local collection failure would not be caught by the existing
workflow.

Recommended fix:

Make pytest collection and a fast pytest subset mandatory. Keep the expensive
model-generation tests as a separate marked job.

### TED-003 - Resolved - old pytest collection failed from repo root

Evidence:

- Local command:
  `MPLCONFIGDIR=/tmp/dynamite-mplconfig .venv/bin/python -m pytest --collect-only -q archive/dev_tests`
- Result:
  - `ImportError` in `archive/dev_tests/test_dataprep.py` because
    `dynamite.data_prep.data_prep_test` is missing.
  - `FileNotFoundError` in `archive/dev_tests/test_decomp.py` because the test opens
    `user_test_config_ml.yaml` at import time from the current working
    directory.

Impact:

The test suite cannot be used as a normal pytest suite. It is currently a set of
executable scripts with test-like names, not a reliable automated test harness.

Recommended fix:

Current status: resolved for the local cleanup baseline. Old development-test
content is archived, and active pytest coverage lives under `tests/`.

Move script work into test functions, resolve fixture paths with
`Path(__file__).parent`, and skip or remove tests that target missing sample
modules.

### TED-004 - Resolved - archived development tests mutate outputs during import or top-level execution

Evidence:

- `archive/dev_tests/test_decomp.py:10-14` constructs `Configuration(...,
  reset_existing_output=True)` at import time.
- `archive/dev_tests/test_decomp.py:16` starts `ModelIterator(c)` at import time.
- `archive/dev_tests/test_nnls.py:34-39` also uses
  `reset_existing_output=True` during its main run.

Impact:

Tests are destructive to their configured output folders and cannot be safely
collected, imported, or partially run. This also makes failures harder to
triage because setup side effects happen before test boundaries exist.

Recommended fix:

Current status: resolved for active local tests because the old workflows are
archived under `archive/dev_tests/`. Keep this as a warning if those archived
scripts are reused.

Use pytest fixtures with temporary output directories, explicit setup phases,
and no model execution at module import time.

### TED-005 - Archived - old shell test scripts assume local shell tools and global install style

Evidence:

- `archive/dev_tests/run_all.sh:14-28` loops over all `*.py`, writes output files in the
  current directory, uses `bc`, deletes/moves log files, and inspects `*.log`.
- `archive/dev_tests/test_all.sh:28-31` tells users to verify installation via
  `python setup.py install --user`.
- `archive/dev_tests/test_all.sh` rewrites configs with shell pipelines and writes
  scenario directories under `archive/dev_tests/test_all`.

Impact:

These are useful human-run scripts, but they are not isolated test runners.
They mutate the working tree and assume global/user install patterns that do
not match the local-only `.venv` rule for this fork audit.

Recommended fix:

Keep them as legacy/manual scripts, but add a modern pytest or nox-style local
runner that writes only to a temporary directory.

### TED-006 - Resolved/Partial - marker strategy separates fast, slow, and optional Fortran tests

Evidence:

- There is no `pytest.ini`, `tox.ini`, or `pyproject.toml` pytest config.
- `archive/dev_tests/` contains fast import-like scripts, long model-generation
  scripts, notebooks, Slurm paths, and solver comparison scripts in one folder.

Impact:

Developers cannot run a dependable "fast local" test set before editing. CI
also cannot express optional jobs cleanly.

Recommended fix:

Current status: partially resolved locally. Active tests use `slow` and
`orblib_fortran` markers plus environment gates for slow/shared-library checks.
No active GALAHAD tests remain because that backend is archived.

Introduce pytest markers such as `unit`, `integration`, `slow`,
`requires_fortran`, `requires_galahad`, `destructive`, and `notebook`.

### TED-007 - Medium - docs build dependencies are not part of package extras or CI

Evidence:

- `docs/more_info/making_the_docs.rst:7-18` lists Sphinx, nbsphinx, pandoc,
  numpydoc, IPython, autodocsumm, and ipykernel as documentation requirements.
- `setup.py:62-67` defines `testing` extras only as `pytest` and `coverage`.
- CI does not build docs.

Impact:

The documentation can drift from the API without automated detection. Notebook
execution is also not exercised by CI.

Recommended fix:

Add a local docs extra or requirements file, and run at least a strict Sphinx
build in a separate CI job. Notebook execution can remain optional/slow.

### TED-008 - Medium - docs and install instructions still mention global or user installs

Evidence:

- `docs/index.rst:48` says to run `python setup.py install`.
- `archive/dev_tests/test_all.sh:28-31` references `python setup.py install --user`.
- `docs/more_info/making_the_docs.rst:10-14` suggests conda or direct pip
  installs for docs dependencies.

Impact:

Those instructions are upstream documentation and may be acceptable upstream,
but they conflict with this fork's local-only audit rule. A local development
guide in `aidocs/` should prefer `.venv` or `uv` commands.

Recommended fix:

Keep upstream docs untouched for now, but document the fork-local setup in
`aidocs/`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[testing]"
```

For a fresh future setup, `uv` is a faster alternative:

```bash
uv venv .venv
uv pip install -e ".[testing]"
```

### TED-009 - Resolved/Partial - executable-script tests lacked assertions around generated science outputs

Evidence:

- `archive/dev_tests/test_nnls.py` compares plotted/model values to a comparison file
  visually and prints tables.
- `archive/dev_tests/run_all.sh` treats a zero process exit as success.

Impact:

Some important regressions may only appear in output files or plots and not
fail the test process.

Recommended fix:

Current status: partially resolved locally. Active slow tests regenerate the
NGC6278 LOSVD workflow and compare against both the historical executable
fixture and the current shared-library fixture. Archived scripts under
`archive/dev_tests/` remain non-authoritative.

Convert scientific comparisons into explicit numeric assertions with tolerances
and recorded expected-output fixtures.

## Local Status

Current cleanup verification used active tests under `tests/`. No upstream docs
or archived `archive/dev_tests/` workflows were run as authoritative tests.

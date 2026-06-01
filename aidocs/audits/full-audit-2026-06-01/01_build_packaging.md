# 01 Build Packaging

Date started: 2026-06-01

## Scope

This audit section covers:

- Python package metadata and editable installation.
- Dependency declaration and resolver behavior.
- Test extras.
- Package data for legacy Fortran executables.
- Fortran build surface, no-GALAHAD build result, and local GALAHAD build
  follow-up.
- CI/build reproducibility risks.

## Evidence Reviewed

- `setup.py`
- `requirements.txt`
- `README.md`
- `.github/workflows/ci.yml`
- `legacy_fortran/Makefile`
- `legacy_fortran/Makefile.linux`
- `legacy_fortran/README.linux`
- `legacy_fortran/compile_deps.sh`
- local `.venv` editable install result
- local no-GALAHAD Fortran build result
- local GALAHAD-backed Fortran build follow-up
- pytest collection result

## Current Build State

Python editable install into `.venv` succeeded with:

```bash
.venv/bin/python -m pip install --no-cache-dir --no-build-isolation -e '.[testing]'
```

`pip check` found no broken requirements.

The no-GALAHAD Fortran build succeeded:

```bash
cd legacy_fortran
make nogal
```

Generated local ignored executables:

- `legacy_fortran/orbitstart`
- `legacy_fortran/orbitstart_bar`
- `legacy_fortran/orblib_new_mirror`
- `legacy_fortran/orblib_bar`

The full GALAHAD-linked build was later run with local vendored dependencies:

```bash
cd legacy_fortran
make GALAHADDIR=/home/reinhard/projects/thomas/dynamite/legacy_fortran/galahad-2.3 GALAHADTYPE=pc.lnx.gfo/double all
```

That build succeeded after repairing generated GALAHAD archives that were
missing `gltr.o` and `hsl_ma57d.o`.

Additional generated local ignored executables:

- `legacy_fortran/triaxmass`
- `legacy_fortran/triaxmass_bar`
- `legacy_fortran/triaxmassbin`
- `legacy_fortran/triaxmassbin_bar`
- `legacy_fortran/triaxnnls_CRcut`
- `legacy_fortran/triaxnnls_noCRcut`
- `legacy_fortran/triaxnnls_bar`

## Findings

### BP-001

Severity: Medium

Area: Test packaging / test discovery

Files:

- `dev_tests/test_dataprep.py`
- `dynamite/data_prep/__init__.py`
- `dynamite/data_prep/`

Summary:

`pytest --collect-only dev_tests` fails because `dev_tests/test_dataprep.py`
imports `data_prep_test` from `dynamite.data_prep`, but that name is not
available.

Evidence:

```text
ImportError: cannot import name 'data_prep_test' from 'dynamite.data_prep'
```

Impact:

The development test suite cannot be collected from a clean editable install.
This blocks routine automated test execution and hides later test failures.

Recommendation:

Decide whether `data_prep_test` was removed, renamed, or never packaged. Then
either restore/export the intended helper or update the test to import the
current API.

Verification:

Run:

```bash
MPLCONFIGDIR=/tmp/dynamite-mplconfig .venv/bin/python -m pytest --collect-only -q dev_tests
```

### BP-002

Severity: Medium

Area: Test invocation / path assumptions

Files:

- `dev_tests/test_decomp.py`
- `dev_tests/user_test_config_ml.yaml`

Summary:

`dev_tests/test_decomp.py` performs configuration construction at import time
and refers to `user_test_config_ml.yaml` as a bare relative path. Collection
from the repository root fails.

Evidence:

```text
FileNotFoundError: [Errno 2] No such file or directory: 'user_test_config_ml.yaml'
```

Impact:

Tests are sensitive to current working directory and can fail before test
execution. Import-time model setup also makes collection expensive and brittle.

Recommendation:

Use paths relative to `__file__`, avoid heavyweight configuration work during
module import, and move setup into fixtures or test functions.

Verification:

Run pytest collection from repository root and from `dev_tests/`; both should
collect consistently.

### BP-003

Severity: Medium

Area: Local runtime environment

Files:

- plotting/import paths using Matplotlib

Summary:

Matplotlib cannot write to `/home/reinhard/.config/matplotlib` in this
execution environment and falls back to a temporary cache directory.

Evidence:

```text
/home/reinhard/.config/matplotlib is not a writable directory
Matplotlib created a temporary cache directory at /tmp/...
```

Impact:

Repeated cache creation can slow imports and cause multiprocessing issues,
especially in plotting-heavy audit/test runs.

Recommendation:

For local audit/test commands, set a writable local or temporary cache path:

```bash
MPLCONFIGDIR=/tmp/dynamite-mplconfig
```

For repeatable local scripts, document this in audit/run instructions.

Verification:

Run import and pytest commands with `MPLCONFIGDIR` set and confirm the warning
does not recur.

### BP-004

Severity: Low

Area: Python compatibility / warning hygiene

Files:

- `dynamite/coloring.py`
- `dynamite/physical_system.py`

Summary:

Importing DYNAMITE on Python 3.12 emits `SyntaxWarning` messages for invalid
escape sequences in docstrings and string literals.

Evidence:

Examples:

```text
SyntaxWarning: invalid escape sequence '\l'
SyntaxWarning: invalid escape sequence '\o'
SyntaxWarning: invalid escape sequence '\c'
```

Impact:

These warnings do not currently block import, but they reduce signal-to-noise
and may become more disruptive under stricter warning settings.

Recommendation:

Convert affected docstrings/strings to raw strings or escape backslashes
properly.

Verification:

Run:

```bash
.venv/bin/python -Werror::SyntaxWarning -c "import dynamite"
```

after cleanup.

### BP-005

Severity: Medium

Area: Dependency lifecycle

Files:

- `requirements.txt`
- `dynamite/coloring.py`

Summary:

Importing DYNAMITE emits a warning that VorBin is deprecated and superseded by
PowerBin, while `requirements.txt` still requires `vorbin>=3.1.4`.

Evidence:

```text
UserWarning: VorBin is deprecated and superseded by PowerBin
```

Impact:

The project depends on a deprecated package at import time. This increases
maintenance risk and may affect future Python compatibility.

Recommendation:

Audit where VorBin is still needed, determine whether PowerBin can replace it,
and avoid importing deprecated functionality at package import time if only
optional workflows need it.

Verification:

Run import checks without the warning after migration or lazy import changes.

### BP-006

Severity: High

Area: CI coverage / packaging verification

Files:

- `.github/workflows/ci.yml`
- `setup.py`

Summary:

The CI workflow does not install the local package unless `pyproject.toml`
exists, but this repository uses `setup.py` and has no `pyproject.toml`.

Evidence:

The CI install step is:

```bash
python -m pip install --upgrade pip
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
if [ -f pyproject.toml ]; then pip install .; fi
if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
```

`pyproject.toml` is absent in this checkout.

Impact:

CI can pass dependency installation without testing whether the package
actually installs. Packaging regressions in `setup.py`, package data, editable
installs, or wheel metadata may not be caught.

Recommendation:

Install the package unconditionally after dependencies, preferably with testing
extras:

```bash
python -m pip install -e ".[testing]"
```

or:

```bash
python -m pip install .
```

Then run tests against the installed package rather than relying only on
`PYTHONPATH`.

Verification:

Update CI and confirm the install step prints DYNAMITE package metadata and
fails if packaging is broken.

### BP-007

Severity: High

Area: CI test execution

Files:

- `.github/workflows/ci.yml`
- `dev_tests/`

Summary:

The CI workflow does not run the pytest suite. It directly executes only
`dev_tests/test_nnls.py`.

Evidence:

The CI test step is:

```bash
# pytest -v
ls
dev_tests/test_nnls.py
```

`dev_tests/test_nnls.py` is executable and has a Python shebang, so this can
run one script, but it is not equivalent to `pytest`.

Impact:

Most development tests are not exercised in CI. Collection failures in
`test_dataprep.py` and `test_decomp.py` would remain invisible if CI only runs
`test_nnls.py`.

Recommendation:

Use pytest explicitly after fixing collection blockers:

```bash
MPLCONFIGDIR=/tmp/dynamite-mplconfig python -m pytest -q dev_tests
```

If full model tests are too expensive, split tests into fast unit tests and
slow integration/model tests with markers.

Verification:

CI should fail on the current collection errors until those are fixed or
properly marked/skipped.

### BP-008

Severity: Medium

Area: Fortran build coverage

Files:

- `.github/workflows/ci.yml`
- `legacy_fortran/Makefile`
- `legacy_fortran/Makefile.linux`
- `legacy_fortran/compile_deps.sh`

Summary:

CI builds only the no-GALAHAD Fortran target (`make nogal`). This verifies
orbit-start and orbit-library executables but not mass-grid or legacy NNLS
executables that require GALAHAD-linked targets.

Evidence:

CI step:

```bash
make nogal
```

Local `make nogal` produced only:

- `orbitstart`
- `orbitstart_bar`
- `orblib_new_mirror`
- `orblib_bar`

The later local GALAHAD follow-up proved that full targets can build in this
checkout, but only after running the GALAHAD installer and manually re-adding
two required generated objects to the static archives. That repair is not part
of CI.

Impact:

The legacy weight solver path and mass calculation executables can break
without CI detection. This is especially relevant because traditional DYNAMITE
installation instructions include GALAHAD and full Fortran compilation.

Recommendation:

Keep `make nogal` as the fast baseline, but add a separate optional or scheduled
job for full GALAHAD-linked builds where licensing and HSL archive
requirements can be satisfied. At minimum, document which solver modes are
covered by CI and which are not.

Verification:

Add explicit artifact checks for each expected executable and document skipped
full-build prerequisites.

## Open Questions

- Does upstream CI run `dev_tests` from the repository root or from within
  `dev_tests/`?
- Is `data_prep_test` an accidentally omitted file, an old API name, or a
  test that should be retired?
- Should local audit scripts always set `MPLCONFIGDIR`?
- Should the generated GALAHAD archive repair be automated in a local preflight,
  or should the vendored GALAHAD make rules be patched for this fork?

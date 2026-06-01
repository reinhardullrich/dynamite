# 00 Environment

Date: 2026-06-01

## Local Install Policy

The audit uses only repository-local installation state.

- Python environment: `.venv/`
- No global Python packages installed.
- No `sudo`, `apt`, or global compiler/library installation used.
- Existing system compiler `/usr/bin/gfortran` is used as an available tool,
  not installed by this audit.

## Python Environment

Created local virtual environment:

```bash
python3 -m venv .venv
```

Observed Python:

```text
Python 3.12.3
```

Packaging tools were upgraded inside `.venv`:

```text
pip 26.1.2
setuptools 82.0.1
wheel 0.47.0
packaging 26.2
```

Editable install command used:

```bash
.venv/bin/python -m pip install --no-cache-dir --no-build-isolation -e '.[testing]'
```

The first install attempt without escalation failed because the sandbox could
not resolve PyPI. The escalated retry was network-enabled and stayed local to
`.venv`. During the download there was an internet outage/timeout; pip resumed
the incomplete `numpy` download and the install completed successfully.

## Python Install Verification

`pip check` result:

```text
No broken requirements found.
```

DYNAMITE package metadata:

```text
Name: dynamite
Version: 5.0.0
Editable project location: /home/reinhard/projects/thomas/dynamite
```

Import sanity check succeeded:

```text
dynamite 5.0.0
numpy 2.3.5
scipy 1.17.1
astropy 7.2.0
matplotlib 3.10.9
```

## Installed Python Package Snapshot

Key installed packages:

```text
astropy==7.2.0
cmasher==1.9.2
coverage==7.14.1
dynamite==5.0.0 editable
h5py==3.16.0
lmfit==1.3.4
matplotlib==3.10.9
numba==0.62.1
numpy==2.3.5
pafit==2.0.8
pathos==0.3.5
plotbin==3.1.8
powerbin==1.1.11
pymc==6.0.1
pytest==9.0.3
PyYAML==6.0.3
scipy==1.17.1
sparse==0.18.0
vorbin==3.2.1
```

## Environment Warnings Observed

Matplotlib import warning:

```text
/home/reinhard/.config/matplotlib is not a writable directory
Matplotlib created a temporary cache directory at /tmp/...
```

Audit implication: local runs that import Matplotlib should set
`MPLCONFIGDIR` to a repo-local or `/tmp` writable path to avoid repeated cache
creation and multiprocessing issues.

DYNAMITE import warnings:

```text
SyntaxWarning: invalid escape sequence '\l'
SyntaxWarning: invalid escape sequence '\o'
SyntaxWarning: invalid escape sequence '\c'
UserWarning: VorBin is deprecated and superseded by PowerBin
```

Audit implication: the SyntaxWarnings are mostly docstring/string-literal
cleanup issues, but they are useful signals for Python-version compatibility.
The VorBin warning is a dependency deprecation risk.

## Fortran Environment

Observed compiler:

```text
GNU Fortran (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
```

No global Fortran dependency installation has been performed.

## Initial Fortran Build Preflight

Existing compiled executables before the audit build check:

```text
none found at legacy_fortran/ top level
```

Dry-run target:

```bash
make -n nogal
```

The dry run shows `nogal` would compile the no-GALAHAD executables:

- `orbitstart`
- `orbitstart_bar`
- `orblib_new_mirror`
- `orblib_bar`

The dry-run uses the repository `legacy_fortran/Makefile` with `gfortran` and
flags including:

```text
-ffast-math -O3 -march=native -fomit-frame-pointer -m64 -funroll-loops
-ftree-loop-linear -std=legacy -fexternal-blas
```

`-ftree-loop-linear` is a candidate portability risk with modern GCC and will
need monitoring on other compilers/platforms. It did not block the local
no-GALAHAD build with GNU Fortran 13.3.0.

## No-GALAHAD Fortran Build Result

Command:

```bash
make nogal
```

Result: succeeded with GNU Fortran 13.3.0.

Executables produced locally under `legacy_fortran/`:

- `orbitstart`
- `orbitstart_bar`
- `orblib_new_mirror`
- `orblib_bar`

The build also produced `.o` and `.mod` files in `legacy_fortran/`. Git status
shows these artifacts are ignored by the repository's `.gitignore`.

## GALAHAD Fortran Build Result

The initial audit pass did not run the full GALAHAD build. This gap was later
closed locally without global/system installation.

Local dependency trees used:

- `legacy_fortran/galahad-2.3/`
- `legacy_fortran/cuter/`
- `legacy_fortran/hsl/`

The GALAHAD installer completed for PC/Linux/GNU gfortran, QP packages, local
CUTEr, and double precision. The first DYNAMITE `make all` attempt then failed
at the final solver link because generated GALAHAD static archives were missing
two required objects:

- `gltr.o` in `libgalahad.a`
- `hsl_ma57d.o` in `libgalahad_hsl.a`

Those objects were compiled into `/tmp/dynamite-galahad-probe` and re-added to
the generated local archives with `ar`/`ranlib`. No source files or Makefiles
were changed.

Full build command:

```bash
cd legacy_fortran
make GALAHADDIR=/home/reinhard/projects/thomas/dynamite/legacy_fortran/galahad-2.3 GALAHADTYPE=pc.lnx.gfo/double all
```

Result: succeeded after the generated-archive repair.

Additional checks:

- `ldd` on `triaxnnls_CRcut`, `triaxnnls_noCRcut`, and `triaxnnls_bar` showed
  no missing dynamic libraries.
- unresolved-symbol scans showed no remaining GALAHAD/HSL symbol references.
- EOF smoke tests reached DYNAMITE input parsing in all three solver binaries.

Runtime GALAHAD/QPB check:

- A real model run in `/tmp/dynamite-galahad-run` completed 5 classic
  `nnls_solver: 1` legacy weight solves.
- Direct solver-mode `5` runs against generated model inputs reached
  `QPB_solve` in both `triaxnnls_noCRcut` and `triaxnnls_CRcut`.
- Both direct GALAHAD runs logged `QPB_solve exit status = -5`, but the shell
  process still exited `0` and wrote output files.

Detailed evidence is recorded in `13_galahad_runtime_check.md`.

## Python Baseline Checks

Compile check:

```bash
MPLCONFIGDIR=/tmp/dynamite-mplconfig .venv/bin/python -m compileall -q dynamite
```

Result: succeeded.

Pytest collection:

```bash
MPLCONFIGDIR=/tmp/dynamite-mplconfig .venv/bin/python -m pytest --collect-only -q dev_tests
```

Result: failed during collection before tests ran.

Collection errors:

1. `dev_tests/test_dataprep.py` imports
   `from dynamite.data_prep import data_prep_test`, but
   `dynamite/data_prep/__init__.py` does not export that name and no obvious
   `data_prep_test` module exists in `dynamite/data_prep/`.
2. `dev_tests/test_decomp.py` constructs a configuration with
   `user_test_config_ml.yaml` as a bare relative path. Collection from the
   repository root fails because that file is under `dev_tests/`.

Warning during collection:

```text
VorBin is deprecated and superseded by PowerBin
```

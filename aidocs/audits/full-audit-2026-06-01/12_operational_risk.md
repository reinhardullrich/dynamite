# 12 Operational Risk Audit

Scope: local development safety, dependency setup, build reproducibility, file
state, generated artifacts, CI/runtime environment assumptions, and destructive
workflows.

## Current local state

- Local Python dependencies are installed in `.venv/`.
- `.venv/`, pytest caches, Python caches, Fortran `.o/.mod` files, Fortran
  executables, and logs are ignored by `.gitignore`.
- Current untracked source/documentation state is `AGENTS.md` and `aidocs/`.
- Current ignored generated state includes `.venv/`, `.pytest_cache/`,
  `__pycache__/`, `legacy_fortran/*.o`, `legacy_fortran/*.mod`, and the
  local Fortran executables.
- Current ignored generated state also includes local GALAHAD installer output
  under `legacy_fortran/galahad-2.3/{makefiles,modules,objects,versions}/`.

## Findings

### OR-001 - Medium - dependency setup is local but not locked

Evidence:

- Local audit setup used `.venv/`, which is ignored by `.gitignore`.
- `requirements.txt` and `setup.py` define dependencies, but there is no
  lockfile or pinned audit environment.
- The install was interrupted by an internet outage and later resumed
  successfully.

Impact:

Fresh installs can drift as PyPI packages release new versions. A later audit
run may not exactly reproduce this one.

Recommended fix:

Create a fork-local lock workflow. `uv` is a good candidate for fast future
setup, but the important operational requirement is a checked-in or archived
environment lock for audit runs.

### OR-002 - High - constructors and test scripts can delete or mutate model output state

Evidence:

- Configuration construction can update `all_models.ecsv` and inspect/delete
  model directories, as recorded in `02_configuration_runtime.md`.
- `dev_tests/test_decomp.py` and `dev_tests/test_nnls.py` use
  `reset_existing_output=True`.
- Development shell scripts write output files and scenario folders under
  `dev_tests/`.

Impact:

Importing or running a script can modify or delete model outputs. This is risky
for ad hoc investigation and makes automated testing difficult.

Recommended fix:

Separate read-only config loading from output-state repair/deletion. Tests
should write into temporary directories unless explicitly run as destructive
integration tests.

### OR-003 - Medium - Fortran build artifacts are ignored but left in-place

Evidence:

- `.gitignore` excludes `legacy_fortran/*.mod`, `legacy_fortran/*.o`, and
  compiled Fortran executables.
- The local `make nogal` run produced ignored artifacts in `legacy_fortran/`.

Impact:

This is normal for local builds, but it can confuse manual inspection because
executables in the tree may not correspond to the current source or compiler
profile.

Recommended fix:

Document that ignored Fortran artifacts are local build outputs. For release or
audit verification, run a clean build and record compiler flags plus executable
hashes.

### OR-004 - High - model-state and cache writes are not atomic

Evidence:

- `05_model_state_iteration.md` records non-atomic `all_models.ecsv` writes.
- `09_analysis_plotting_coloring.md` records cache metadata written before
  `.npz` data in coloring workflows.
- Many tables are written with `overwrite=True` directly to final paths.

Impact:

Interrupted runs can leave partial or internally inconsistent model state.
Later runs may treat stale cache metadata or incomplete tables as valid.

Recommended fix:

Use temporary files plus atomic replacement for model tables, weight files,
cache metadata, and derived analysis products.

### OR-005 - Medium - full Fortran/GALAHAD setup is local but fragile

Evidence:

- `legacy_fortran/compile_deps.sh` requires `HSLARCHIVE` and clones several
  repositories into `legacy_fortran/`.
- This checkout contains local `galahad-2.3`, `cuter`, and `hsl` trees, and
  the full GALAHAD-backed solver compilation now succeeds after a generated
  archive repair.
- The local GALAHAD installer left `gltr.o` and `hsl_ma57d.o` out of generated
  static archives, causing the first full DYNAMITE link attempt to fail.

Impact:

The full solver backend can be built locally in this checkout, but a fresh
rebuild is not fully scripted or self-checking. A developer can have compiled
modules present while the static archives are still missing required members.

Recommended fix:

Add a full-backend preflight that checks local GALAHAD/CUTEr/HSL paths,
compiler path, expected output directories, and required archive members before
running dependency compilation or DYNAMITE `make all`.

### OR-006 - Medium - CI uses global/system installation patterns

Evidence:

- `.github/workflows/ci.yml` installs `gfortran` with `sudo apt-get`.
- Upstream docs mention `python setup.py install` and user/global package
  installation patterns.

Impact:

That is normal in disposable CI, but it differs from this fork's local-only
development rule. Developers should not copy CI commands into the local
workspace without considering scope.

Recommended fix:

Keep the fork-local setup guide in `aidocs/` and use `.venv` or `uv` locally.
Ask before any global/system install.

### OR-007 - Medium - headless Matplotlib needs an explicit writable config/cache directory

Evidence:

- Local import/compile checks produced Matplotlib config warnings until
  `MPLCONFIGDIR=/tmp/dynamite-mplconfig` was used.

Impact:

On locked-down systems or sandboxed runs, Matplotlib can create temporary cache
directories and slow imports or produce noisy logs.

Recommended fix:

For local audit commands, set:

```bash
MPLCONFIGDIR=/tmp/dynamite-mplconfig
```

Longer term, test runners should set this automatically.

### OR-008 - Medium - shell-script workflows are not hardened for failure

Evidence:

- Generated backend scripts in orbit/weight workflows touch completion files
  after running commands, but earlier audit sections found missing `set -e` and
  weak return-code checks.
- `dev_tests/run_all.sh` and `test_all.sh` rely on shell-side mutation and
  output-file inspection.

Impact:

Failures can be masked or diagnosed only after manual log inspection.

Recommended fix:

Add strict shell options in generated scripts, check command return codes, and
validate outputs before writing done markers.

### OR-009 - Low - package data includes optional executables only if already built

Evidence:

- `setup.py` lists Fortran executables in `package_data`, and appends several
  optional legacy executables only if `os.path.isfile(e)` is true at setup time.

Impact:

The installed package can differ depending on what happened to be compiled
before installation.

Recommended fix:

Make executable packaging explicit: either build as part of the install process,
ship no executables and require local build, or fail with a clear message when
required binaries are absent.

## Local Operating Rule

For this fork, keep all installs local to the repository unless the user
explicitly approves otherwise. The current local Python environment is `.venv/`.
No global Python packages, system package manager operations, or `sudo` commands
should be used from Codex.

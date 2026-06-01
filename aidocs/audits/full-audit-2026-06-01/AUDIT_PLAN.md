# Full Audit Plan

Date started: 2026-06-01

## Scope

Run a proper full audit of the local DYNAMITE fork at:

```text
/home/reinhard/projects/thomas/dynamite
```

The audit covers repository structure, Python package behavior, Fortran
backend behavior, build/install workflow, tests/examples, numerical/scientific
risks, and operational risks.

## Write Boundaries

Allowed write targets for this audit:

- `.venv/` for local Python dependencies.
- `aidocs/audits/full-audit-2026-06-01/` for audit notes and findings.
- `aidocs/KNOWLEDGE.md` and `aidocs/CHANGES.md` for local documentation state.

Do not modify these areas unless explicitly requested:

- upstream `docs/`
- Python package source under `dynamite/`
- Fortran source/build files under `legacy_fortran/`
- development tests/examples under `dev_tests/`

## Install Rule

Install dependencies only locally inside this repository.

Allowed local install pattern:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --no-cache-dir -U pip setuptools wheel
python -m pip install --no-cache-dir -e ".[testing]"
```

No global installs are allowed without asking first.

Stop and ask before using:

- `sudo`
- `apt`
- system package managers
- global `pip install`
- global compiler/library installation
- modifying system compiler or linker configuration

Existing system tools such as `/usr/bin/gfortran` may be used without
installing anything globally.

## Natural Audit Split

### 1. Repository / Build / Packaging

Files and surfaces:

- `setup.py`
- `requirements.txt`
- `.github/`
- local editable install
- package data for Fortran executables
- dependency constraints
- fork/remotes hygiene

Questions:

- Can the project install cleanly in a local venv?
- Are dependencies pinned enough for reproducibility?
- Are compiled Fortran executables packaged correctly?
- Does CI reflect real user install/test paths?

### 2. Configuration And Runtime Bootstrap

Files and surfaces:

- `dynamite/config_reader.py`
- `dynamite/constants.py`
- logging setup
- YAML parsing and validation
- output directory creation
- resume/bootstrap behavior

Questions:

- Are config validation errors clear and early?
- Are unknown keys rejected consistently?
- Can output reset paths delete data unexpectedly?
- Does bootstrapping correctly reconcile disk state and table state?

### 3. Physical Model And Parameter Space

Files and surfaces:

- `dynamite/physical_system.py`
- `dynamite/parameter_space.py`

Questions:

- Are component combinations validated correctly?
- Are dark halo, black-hole, visible-component, and barred-system assumptions
  explicit and safe?
- Are parameter transforms, bounds, and step sizes robust?
- Do parameter generators avoid duplicates and invalid states reliably?

### 4. Data Ingestion

Files and surfaces:

- `dynamite/data.py`
- `dynamite/mges.py`
- `dynamite/kinematics.py`
- `dynamite/populations.py`
- `dynamite/data_prep/`

Questions:

- Are input formats validated robustly?
- Are ECSV/old-format conversions safe?
- Are MGE axis ratios and kinematic uncertainty assumptions checked?
- Are BayesLOSVD and Gauss-Hermite paths consistent?

### 5. Model State And Iteration

Files and surfaces:

- `dynamite/model.py`
- `dynamite/model_iterator.py`
- `all_models.ecsv`
- output model directory layout
- multiprocessing pools

Questions:

- Are model table state and on-disk state reconciled safely?
- Are retries and failure states explicit?
- Can multiprocessing race on shared orbit-library directories?
- Does `ml`-only orbit-library reuse work correctly?

### 6. Orbit Library Boundary

Files and surfaces:

- `dynamite/orblib.py`
- generated `infil/` files
- generated `datfil/` files
- status files such as `tube_done`, `box_done`, `tube_box_done`

Questions:

- Is the Python-to-Fortran contract explicit and validated?
- Are external process failures detected reliably?
- Are required files checked before downstream use?
- Are orbit-library reuse and mirroring behaviors correct?

### 7. Weight Solving / Optimization

Files and surfaces:

- `dynamite/weight_solvers.py`
- `LegacyWeightSolver`
- `NNLS`
- SciPy and optional cvxopt paths

Questions:

- Are solver success/failure states detected correctly?
- Are chi-square values computed and stored consistently?
- Are regularization and mass constraints applied correctly?
- Are solver-specific assumptions documented and validated?

### 8. Legacy Fortran Backend

Files and surfaces:

- `legacy_fortran/`
- `legacy_fortran/Makefile`
- `legacy_fortran/Makefile.linux`
- GALAHAD/CUTEst/HSL integration

Subsections:

- orbit initial conditions
- orbit integration/library generation
- mass grid calculations
- legacy NNLS/GALAHAD solvers
- build flags and compiler assumptions

Questions:

- Can no-GALAHAD targets build locally?
- What blocks full GALAHAD build locally?
- Are compiler flags portable and safe?
- Are Fortran runtime failures surfaced to Python?

### 9. Analysis / Plotting / Coloring

Files and surfaces:

- `dynamite/analysis.py`
- `dynamite/plotter.py`
- `dynamite/coloring.py`

Questions:

- Are post-processing assumptions tied to model/table state correctly?
- Are plots robust against partial or failed model runs?
- Does coloring/population analysis handle missing or inconsistent inputs?

### 10. Tests / Examples / Docs

Files and surfaces:

- `dev_tests/`
- tutorial configs and notebooks under upstream `docs/`
- `.github/workflows/ci.yml`

Questions:

- Which workflows are covered by executable tests?
- Which examples depend on compiled Fortran or external data?
- Are notebooks stale relative to current APIs?
- Does CI catch packaging/build/runtime failures?

### 11. Scientific / Numerical Correctness

Cross-cutting scope:

- model assumptions
- convergence
- halo domains
- MGE deprojection
- orbit sampling
- solver behavior
- chi-square interpretation

Questions:

- Are physical parameter domains enforced?
- Are numerical singularities and invalid domains handled?
- Are stopping criteria scientifically defensible?
- Are results reproducible enough for research use?

### 12. Operational Risk

Cross-cutting scope:

- destructive commands
- output reset behavior
- disk usage
- multiprocessing
- reproducibility
- local/global install boundaries

Questions:

- What can delete or overwrite user data?
- What can consume large disk/CPU resources unexpectedly?
- What depends on implicit system state?
- What should be documented before serious local development?

## Execution Order

1. Record local environment and installation attempts in `00_environment.md`.
2. Build local Python venv and install editable package with testing extras.
3. Run import/package sanity checks.
4. Attempt safe Fortran build checks, starting with no-GALAHAD targets.
5. Audit build/packaging first because later checks depend on environment.
6. Audit Python runtime modules in the split above.
7. Audit Fortran backend and Python/Fortran boundary.
8. Audit tests/examples/docs.
9. Produce `SUMMARY.md` with prioritized findings.

## Finding Format

Use this structure for actionable findings:

```text
ID:
Severity:
Area:
Files:
Summary:
Evidence:
Impact:
Recommendation:
Verification:
```

Severity scale:

- `Critical`: can produce invalid scientific results, major data loss, or
  severe security/operational failure.
- `High`: likely runtime failure, silent wrong result, or serious
  reproducibility issue.
- `Medium`: meaningful correctness, maintainability, or test coverage risk.
- `Low`: localized cleanup, clarity, or documentation issue.

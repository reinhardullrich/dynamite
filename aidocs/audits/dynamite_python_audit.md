# DYNAMITE Python Code Audit

Date: 2026-06-01

Repository audited: `/home/reinhard/projects/thomas/dynamite`

I did not modify the cloned repository. This report is a static code review plus packaging/dependency inspection. I could not run the project test suite locally because this environment does not have the scientific Python stack installed (`numpy`, `scipy`, `astropy`, `pytest`, and `setuptools` were missing). I did run syntax parsing for the package modules and validated the requirement strings with `packaging`.

## Executive Summary

DYNAMITE is a mature scientific Python package around a legacy Fortran modelling pipeline. The Python side handles configuration, data ingestion, orbit-library orchestration, weight solving, analysis, and plotting. The most important risks I found are not style issues; they are correctness and reproducibility risks:

- Orbit-library shell scripts can mark failed Fortran runs as complete.
- `pip install .` is likely broken because `setup.py` passes comment lines from `requirements.txt` directly to `install_requires`.
- Several analytic dark-halo methods contain clear runtime errors or incorrect parameter unpacking.
- Importing `dynamite` eagerly imports heavy optional plotting/Bayesian dependencies such as `pymc`, `vorbin`, and `powerbin`.
- Runtime validation often uses `assert`, including at least one tautological assertion that never checks the intended condition.
- The test and CI setup does not currently exercise installation via `setup.py`, and the local tests are integration scripts rather than discoverable unit tests.

## Validation Performed

- Confirmed `git status --short` in the cloned repo was clean.
- Parsed all package Python files plus `setup.py` with `ast.parse`: package files parse successfully under Python 3.12.
- Warnings from parse:
  - `dynamite/coloring.py`: invalid escape sequences in docstrings/labels such as `\l` and `\o`.
  - `dynamite/physical_system.py`: invalid escape sequence `\c`.
- Validated `requirements.txt` entries using `packaging.requirements.Requirement`.
- Inspected current PyPI release pages for the main dependencies.
- Inspected CI config in `.github/workflows/ci.yml`.

## Findings

### P0: Orbit-library scripts can falsely mark failed runs complete

Files:

- `dynamite/orblib.py:488`
- `dynamite/orblib.py:501`
- `dynamite/orblib.py:579`
- `dynamite/orblib.py:588`
- `dynamite/orblib.py:605`
- `dynamite/orblib.py:622`
- `dynamite/orblib.py:637`
- `dynamite/orblib.py:671`
- `dynamite/orblib.py:688`
- `dynamite/orblib.py:708`
- `dynamite/orblib.py:717`

`write_executable_for_integrate_orbits_par()` and `write_executable_for_integrate_orbits()` generate shell scripts without `set -e` or explicit failure handling for the Fortran orbit integration commands. In both parallel and sequential modes, the generated scripts can execute the Fortran program, then continue to compression/removal commands, and finally `touch datfil/tube_done` or `touch datfil/box_done`.

The Python caller treats empty shell stdout as success:

- `get_orbit_library_par()` checks `if not p.stdout.decode("UTF-8")`.
- `get_orbit_library()` does the same for tube and box scripts.

Because the Fortran program output is redirected into log files, a failing command can produce no captured stdout. In the parallel script, `wait $orblib $orblibbox` is not paired with robust error propagation. This can leave the system believing an orbit library is complete when outputs are missing, partial, or inconsistent.

Impact:

- Corrupt or incomplete orbit libraries can be reused.
- Downstream weight solving may read broken files or silently produce bad scientific results.
- Done flags become unreliable.

Recommended fix:

- Generate scripts with `set -euo pipefail`.
- Append `|| exit 1` to every critical executable, decompression, compression, and move step.
- Only touch completion flags after expected output files exist and pass minimal sanity checks.
- Prefer `subprocess.run(["bash", cmdstr], cwd=self.mod_dir, check=True, capture_output=True, text=True)` over `os.chdir` and `shell=True`.

### P0: `pip install .` can fail because comment lines are passed as requirements

Files:

- `setup.py:13`
- `setup.py:15`
- `setup.py:55`
- `requirements.txt:13`
- `requirements.txt:14`
- `requirements.txt:15`

`setup.py` reads `requirements.txt` with `fp.read().splitlines()` and passes the result directly to `install_requires`. The requirements file contains comment lines explaining the SciPy constraint. Those comment strings are invalid PEP 508 requirement specifiers.

Local validation result:

```text
13: '# scipy nnls: re-written in Python in v1.12, much slower than before and' -> Expected package name at the start of dependency specifier
14: '# tends to fail; re-written in Cython in v1.15, still slower than before;' -> Expected package name at the start of dependency specifier
15: '# re-written in C in v1.16, fast again. Avoid versions 1.12 to 1.15.' -> Expected package name at the start of dependency specifier
```

Impact:

- The documented install command `python -m pip install .` may fail under modern packaging tooling.
- CI does not catch this because `.github/workflows/ci.yml` only runs `pip install .` if `pyproject.toml` exists, and the repo has no `pyproject.toml`.

Recommended fix:

- Filter blank/comment lines before passing to `install_requires`, or move metadata to `pyproject.toml`.
- Update CI to always run `python -m pip install .` after installing build dependencies.

### P1: Dark-halo analytic methods contain runtime errors and likely physics bugs

File: `dynamite/physical_system.py`

Problem areas:

- `NFW_m200_c.rhoc()` at `physical_system.py:1233` uses bare `log` and `rhocrit`.
- `NFW_m200_c.rc()` at `physical_system.py:1235` uses bare `pi`.
- `NFW_m200_c.M200()` at `physical_system.py:1237` uses `rc` as if it were a value, not `rc(c, f)`.
- `NFW_m200_c.potential()` at `physical_system.py:1243` uses bare `G`, `sqrt`, `log`, `atanh`, and compares against bare `rc` at `physical_system.py:1244`.
- `Hernquist.potential()` at `physical_system.py:1280` uses undefined `G`.
- `Hernquist.mass_enclosed()` at `physical_system.py:1291` uses `r` without defining it.
- `TriaxialCoredLogPotential.par_names` is `['Vc', 'Rc', 'p', 'q']` at `physical_system.py:1302`, but methods unpack `rc, vc, p, q` at `physical_system.py:1312`, `physical_system.py:1318`, and `physical_system.py:1325`.
- `TriaxialCoredLogPotential.density()` and `mass_enclosed()` use undefined `G` at `physical_system.py:1320` and `physical_system.py:1332`.
- `TriaxialCoredLogPotential.mass_enclosed()` computes `Menc` but never returns it.

Impact:

- Calling these public methods can raise `NameError`, return `None`, or use swapped physical parameters.
- If these methods are currently only lightly used because legacy Fortran handles most dark-halo work, that is still an under-tested public API problem.

Recommended fix:

- Add tests that call every dark component's `potential`, `density`, `mass_enclosed`, and `acceleration` methods with representative parameters.
- Replace bare functions/constants with `np.*` and constants from `dynamite.constants`.
- Align unpacking with `par_names`.
- Add explicit returns.

### P1: Top-level import forces heavy optional dependencies

Files:

- `dynamite/__init__.py:1`
- `dynamite/coloring.py:4`
- `dynamite/coloring.py:9`
- `dynamite/coloring.py:13`
- `dynamite/coloring.py:14`

`dynamite/__init__.py` imports nearly every package module eagerly. That imports `coloring.py`, which imports `matplotlib`, `scipy`, `yaml`, `pymc`, `cmasher`, `vorbin`, and `powerbin` at module load time.

Impact:

- `import dynamite` fails if `pymc` or plotting/binning extras are missing, even if the user only wants configuration, data handling, or model iteration.
- PyMC is a large Bayesian stack and should not be required for core non-coloring workflows.
- This increases installation fragility and import time.

Recommended fix:

- Make `__init__.py` minimal: expose version and perhaps core modules lazily.
- Move optional plotting/coloring/Bayesian dependencies into extras, e.g. `dynamite[coloring]`, `dynamite[plotting]`.
- Import `pymc`, `vorbin`, and `powerbin` inside the methods that need them.

### P1: Runtime validation uses `assert`, including one check that is definitely wrong

Files:

- `dynamite/kinematics.py:494`
- `dynamite/kinematics.py:662`
- `dynamite/kinematics.py:694`
- `dynamite/kinematics.py:1405`
- `dynamite/weight_solvers.py:611`
- `dynamite/config_reader.py:1112`
- `dynamite/orblib.py:1032`
- `dynamite/orblib.py:1076`
- `dynamite/orblib.py:1079`
- `dynamite/orblib.py:1082`
- `dynamite/data.py:117`
- `dynamite/data.py:118`
- `dynamite/data.py:119`
- `dynamite/parameter_space.py:230`

These are runtime input/data checks, not internal invariants. Python removes asserts under `python -O`, so invalid user data or configuration can pass silently in optimized mode.

One check is also clearly tautological:

```python
assert v_mu.shape==v_mu.shape
```

That is almost certainly intended to compare `v_mu.shape` to `v_sig.shape`.

Impact:

- Production/cluster runs with optimized Python can skip validation.
- The tautological assertion cannot catch mismatched velocity arrays.

Recommended fix:

- Replace these with explicit `if ...: raise ValueError(...)` or `TypeError(...)`.
- Fix the velocity shape check.

### P1: Mutable default arguments can leak state between objects

Files:

- `dynamite/physical_system.py:385`
- `dynamite/physical_system.py:389`
- `dynamite/physical_system.py:390`
- `dynamite/physical_system.py:391`
- `dynamite/parameter_space.py:367`
- `dynamite/parameter_space.py:721`
- `dynamite/parameter_space.py:861`
- `dynamite/parameter_space.py:1060`
- `dynamite/parameter_space.py:1278`
- `dynamite/model_iterator.py:37`
- `dynamite/model_iterator.py:421`
- `dynamite/physical_system.py:1034`

Several constructors and methods use list/dict defaults such as `kinematic_data=[]`, `parameters=[]`, `par_space=[]`, `model_kwargs={}`, and `rows_orblib=[]`.

Impact:

- Calls that omit these arguments share one object across all instances.
- This can create state leakage between physical components, parameter generators, or model directory assignments.

Recommended fix:

- Use `None` as the default and create a fresh list/dict inside the function.

### P1: `os.chdir` plus `shell=True` makes execution fragile

Files:

- `dynamite/orblib.py:452`
- `dynamite/orblib.py:460`
- `dynamite/orblib.py:483`
- `dynamite/orblib.py:488`
- `dynamite/orblib.py:522`
- `dynamite/orblib.py:527`
- `dynamite/orblib.py:553`
- `dynamite/orblib.py:557`
- `dynamite/orblib.py:825`
- `dynamite/orblib.py:834`
- `dynamite/orblib.py:890`
- `dynamite/orblib.py:893`
- `dynamite/orblib.py:993`
- `dynamite/orblib.py:995`
- `dynamite/weight_solvers.py:313`
- `dynamite/weight_solvers.py:324`
- `dynamite/model.py:245`

Many methods change the process-wide current directory, run shell strings, and then manually restore the directory. If an exception occurs before the restore, later relative paths can point to the wrong directory. Several shell commands also interpolate paths/values directly.

Impact:

- Hard-to-debug failures in long model runs.
- Paths with spaces or shell metacharacters can break commands.
- In untrusted configuration contexts, shell injection is possible.

Recommended fix:

- Use `subprocess.run([...], cwd=..., check=True)` with list arguments.
- Use `try/finally` if `os.chdir` remains.
- Avoid shell redirection by using file handles, e.g. `stdout=out_file`.
- Use `tempfile` for decompression outputs.

### P2: `MGE.__add__` mutates both input tables

File: `dynamite/mges.py`

`MGE.__add__()` assigns:

- `mge1_data = self.data`
- `mge2_data = other.data`

It then adds a helper column `row_merge_ID` to both tables before joining. The helper column is removed only from the joined output, not from the original input tables.

Impact:

- Adding two MGEs leaves extra columns in the original objects.
- Later writes, joins, or computations can see polluted input tables.

Recommended fix:

- Copy both tables before adding helper columns:

```python
mge1_data = self.data.copy(copy_data=True)
mge2_data = other.data.copy(copy_data=True)
```

### P2: Text parsers fail on blank lines

Files:

- `dynamite/data.py:144`
- `dynamite/data.py:165`
- `dynamite/mges.py:279`

These list comprehensions check comments with `line.lstrip(' ')[0] != '#'`. A blank or whitespace-only line makes `line.lstrip(' ')` empty and raises `IndexError`.

Impact:

- User input files with harmless blank lines fail with non-obvious errors.

Recommended fix:

- Strip first, skip empty/comment lines:

```python
clean = line.strip()
if clean and not clean.startswith("#"):
    ...
```

### P2: HDF5 loader logs missing files but continues, and does not close the file

File: `dynamite/kinematics.py`

`BayesLOSVD.load_hdf5()` logs if the file is missing at `kinematics.py:1054`, but then continues to `h5py.File(filename, 'r')` at `kinematics.py:1058`. The file handle is not wrapped in a context manager.

Impact:

- Missing files produce a later lower-level exception rather than a clear `FileNotFoundError`.
- File handles can leak.

Recommended fix:

- Raise immediately if the file is missing.
- Use `with h5py.File(filename, "r") as f:`.

### P2: Global logging reset is hostile library behavior

File: `dynamite/config_reader.py`

`DynamiteLogging.__init__()` calls:

- `logging.shutdown()` at `config_reader.py:1224`
- `importlib.reload(logging)` at `config_reader.py:1225`

Impact:

- This resets global logging for the entire process.
- In notebooks, pipelines, or applications embedding DYNAMITE, this can remove unrelated handlers and surprise users.

Recommended fix:

- Configure only a `dynamite` named logger.
- Avoid reloading the stdlib `logging` module.
- If a full reset is needed for scripts, make it opt-in and clearly scoped.

### P2: Configuration has side effects before full validation

File: `dynamite/config_reader.py`

`Configuration.__init__()` creates or removes output directories at `config_reader.py:246` through `config_reader.py:251`, before the full configuration is parsed and validated.

Impact:

- A bad config can still modify the output tree.
- `reset_existing_output=True` can remove output before all later config errors are known.

Recommended fix:

- Parse and validate the full configuration first.
- Perform filesystem mutations after validation.

### P2: Parameter identity uses `np.allclose`

Files:

- `dynamite/model.py:581`
- `dynamite/model.py:584`
- `dynamite/model_iterator.py:412`

Model and orbit-library identity is determined with `np.allclose` over parameter tuples.

Impact:

- Distinct parameter sets that are numerically close can be treated as the same model/orbit library.
- This is especially risky when directory names and persisted model tables are expected to be exact identifiers.

Recommended fix:

- Use formatted parameter keys based on each parameter's declared format/tolerance.
- If tolerance is intended, make it explicit per parameter and log collisions.

### P2: BayesLOSVD bin-ID mapping can index out of bounds

File: `dynamite/kinematics.py`

`map_binID_blosvd_to_binID_dynamite()` uses `np.digitize()` and immediately indexes `srt_binid_dynamite[index]` at `kinematics.py:1290`. If an input `binID_blosvd` is larger than all known values, `index == len(srt_binid_dynamite)`, causing an `IndexError` before missing entries are replaced with zero.

Impact:

- Unexpected external BayesLOSVD bin IDs can crash mapping.

Recommended fix:

- Use a dict mapping `{BayesLOSVD_bin: dynamite_bin}` or mask invalid indices before indexing.

### P2: Broad bare `except:` blocks hide root causes

Examples:

- `dynamite/config_reader.py:214`
- `dynamite/config_reader.py:240`
- `dynamite/parameter_space.py:392`
- `dynamite/parameter_space.py:399`
- `dynamite/model.py:265`
- `dynamite/model.py:924`
- `dynamite/orblib.py:1126`
- `dynamite/orblib.py:1146`
- `dynamite/model_iterator.py:103`

Impact:

- Real programming errors can be converted into generic user-facing errors.
- Debugging model failures becomes harder.

Recommended fix:

- Catch expected exception classes.
- Chain exceptions with `raise ValueError(...) from e` where a domain-specific error is useful.

### P3: Syntax warnings from invalid escape sequences

Files:

- `dynamite/coloring.py`
- `dynamite/physical_system.py`

The package parses, but Python emits syntax warnings for invalid escape sequences in docstrings and plot labels.

Impact:

- No immediate runtime break, but this creates warning noise and future compatibility risk.

Recommended fix:

- Use raw strings for docstrings/labels containing LaTeX-style backslashes, or escape the backslashes.

### P3: Vendored legacy Python 2 file does not parse under Python 3

File:

- `legacy_fortran/galahad-2.3/python/galahad.py`

The package modules parse, but this vendored legacy file contains Python 2 syntax such as `print "..."`.

Impact:

- Any tool that recursively parses all `*.py` files in the repo will fail.
- It is probably not shipped as a Python package because `setuptools.find_packages()` only picks package directories, but it is still a repo-maintenance issue.

Recommended fix:

- Exclude vendored legacy Python 2 files from Python 3 linting/parsing tools.
- Consider renaming or clearly documenting it as legacy/non-Python-3 code.

## Dependency And Packaging Review

Current `requirements.txt`:

```text
astropy>=5.0.4
cmasher>=1.6.0
h5py>=3.1.0
lmfit
matplotlib>=3.5.3
numpy>=1.26
pafit>=2.0.8
pathos>=0.2.7
plotbin>=3.1.7
powerbin
pymc
PyYAML>=5.4.1
scipy>=1.11,!=1.12.*,!=1.13.*,!=1.14.*,!=1.15.*
six
sparse>=0.14.0
vorbin>=3.1.4
numba<0.63
```

Checked current PyPI versions on 2026-06-01:

| Package | Requirement | Current PyPI | Notes |
|---|---:|---:|---|
| numpy | `>=1.26` | 2.4.6 | Allows NumPy 2.x and future majors without an upper bound. |
| scipy | `>=1.11, !=1.12.*, !=1.13.*, !=1.14.*, !=1.15.*` | 1.17.1 | Constraint deliberately avoids slow/problematic NNLS releases. Allows 1.16+ and 1.17+. |
| numba | `<0.63` | 0.65.1 | Requirement intentionally blocks latest Numba. There is no lower bound, so resolver may choose an old compatible version. |
| pymc | unpinned | 6.0.1 | Latest PyMC requires Python >=3.12; DYNAMITE declares Python >=3.10. This can create resolver conflicts for Python 3.10/3.11. |
| astropy | `>=5.0.4` | 7.2.0 | Latest requires Python >=3.11; DYNAMITE declares Python >=3.10. |
| matplotlib | `>=3.5.3` | 3.10.9 | Lower bound is old but current supports Python >=3.10. |
| h5py | `>=3.1.0` | 3.16.0 | Lower bound is old but current supports Python >=3.10. |
| PyYAML | `>=5.4.1` | 6.0.3 | Fine, though lower bound is old. |
| cmasher | `>=1.6.0` | 1.9.2 | Fine. |
| lmfit | unpinned | 1.3.4 | Should have a lower bound. |
| pafit | `>=2.0.8` | 2.0.8 | Current equals requirement. |
| pathos | `>=0.2.7` | 0.3.5 | Fine, but pathos uses multiprocess/dill stack; test parallel flows. |
| plotbin | `>=3.1.7` | 3.1.8 | Current package license says non-commercial/redistribution restrictions; worth reviewing for project distribution policy. |
| powerbin | unpinned | 1.1.11 | Should have a lower bound. |
| sparse | `>=0.14.0` | 0.18.0 | Latest declares Python >=3.11; DYNAMITE declares Python >=3.10. |
| vorbin | `>=3.1.4` | 3.2.1 | PyPI page says VorBin is deprecated and superseded by PowerBin. |
| six | unpinned | 1.17.0 | Appears unused in package code. |

Package-management risks:

- No `pyproject.toml`; project is still using legacy `setup.py` metadata.
- CI skips `pip install .` because it only runs that command if `pyproject.toml` exists.
- Several dependencies are unpinned or lower-bound-only in a scientific codebase with compiled/numerical packages.
- The declared `python_requires=">=3.10"` is now in tension with latest PyPI releases of important dependencies such as `astropy`, `scipy`, `numpy`, `pymc`, and `sparse`, many of which have moved to Python >=3.11 or >=3.12.
- `pymc` should almost certainly be an optional extra, not a core install dependency.
- `vorbin` is deprecated upstream and the code already imports `PowerBin`, so migration should be planned.

Suggested packaging direction:

- Add `pyproject.toml` with PEP 621 metadata.
- Split dependencies into core and extras:
  - core: `numpy`, `scipy`, `astropy`, `h5py`, `PyYAML`, perhaps `sparse`.
  - plotting: `matplotlib`, `cmasher`, `plotbin`, `pafit`.
  - coloring: `pymc`, `powerbin`, maybe `vorbin` while still needed.
  - parallel: `pathos` if it can be optional.
  - cvxopt: existing optional extra.
- Add explicit lower bounds for unpinned packages.
- Add a constraints file for tested environments.
- Decide whether Python 3.10 is still supported. If yes, cap dependencies accordingly. If not, update `python_requires` and classifiers.

## Test And CI Review

Files:

- `.github/workflows/ci.yml`
- `dev_tests/test_nnls.py`
- `dev_tests/test_orbit_losvds.py`

CI currently:

- Tests Python 3.11, 3.12, 3.13.
- Installs `requirements.txt`.
- Only installs the project if `pyproject.toml` exists.
- Builds legacy Fortran with `make nogal`.
- Runs `dev_tests/test_nnls.py` directly as an executable script.
- Has `pytest -v` commented out.

Concerns:

- It does not test the documented install path (`python -m pip install .`).
- It does not catch the `setup.py`/comment-lines problem.
- It mostly exercises a heavy integration path, not fast unit tests around pure-Python helpers.
- There is no `pytest.ini`, `tox.ini`, `noxfile.py`, or standard test layout.

Recommended test improvements:

- Add fast unit tests for:
  - requirement parsing/install metadata,
  - dark-halo analytic methods,
  - `MGE.__add__` not mutating inputs,
  - aperture/bin file parsing with blank lines,
  - BayesLOSVD bin-ID mapping edge cases,
  - validation replacing asserts.
- Keep Fortran model runs as marked integration tests.
- Run `python -m pip install .` in CI.
- Add a lint/parse job that excludes vendored legacy Python 2 files.

## Prioritized Fix Plan

1. Fix packaging first:
   - Filter comments from `requirements.txt` in `setup.py` or move to `pyproject.toml`.
   - Make CI run `python -m pip install .`.

2. Harden orbit-library execution:
   - Replace shell-string execution with checked subprocess calls.
   - Add fail-fast shell settings until the shell scripts can be removed.
   - Only touch done flags after output validation.

3. Fix clear correctness bugs:
   - Dark-halo analytic methods.
   - `kinematics.py:494` tautological assertion.
   - BayesLOSVD bin-ID mapping.
   - `MGE.__add__` input mutation.

4. Improve import/dependency boundaries:
   - Make `pymc`, `vorbin`, `powerbin`, and plotting dependencies optional/lazy.
   - Remove unused `six` if confirmed unused.

5. Add focused unit tests:
   - Start with pure-Python tests that do not require Fortran.
   - Keep the existing `dev_tests` as integration/regression tests.

## Source URLs Used For Dependency Status

- https://pypi.org/project/numpy/
- https://pypi.org/project/scipy/
- https://pypi.org/project/numba/
- https://pypi.org/project/pymc/
- https://pypi.org/project/astropy/
- https://pypi.org/project/matplotlib/
- https://pypi.org/project/h5py/
- https://pypi.org/project/PyYAML/
- https://pypi.org/project/cmasher/
- https://pypi.org/project/plotbin/
- https://pypi.org/project/vorbin/
- https://pypi.org/project/lmfit/
- https://pypi.org/project/pafit/
- https://pypi.org/project/powerbin/
- https://pypi.org/project/pathos/
- https://pypi.org/project/sparse/
- https://pypi.org/project/six/

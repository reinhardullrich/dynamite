# 11 Scientific and Numerical Correctness Audit

Scope: cross-cut correctness risks affecting scientific interpretation,
including model parameter domains, unit handling, numerical integration,
solver status, reproducibility, and derived analysis products.

Current-status update, 2026-06-02: this chapter has been adapted for the
`fortran-cleanup` branch. Active orbit generation uses the direct
shared-library API in `orblib_fortran/`. Legacy NNLS/GALAHAD solver programs
and mass helpers are archived under `archive/legacy_nnls_fortran/`, so solver
status caveats apply to archived solver code unless that backend is explicitly
restored.

This is not a validation of the DYNAMITE scientific method itself. The core
Schwarzschild/MGE workflow is a known astronomy modelling approach. This audit
focuses on implementation guardrails that decide whether a particular run is
safe to trust.

## Findings

### SNC-001 - High - numerical integration warnings do not consistently invalidate model outputs

Evidence:

- `dynamite/mges.py:490-496` logs an intrinsic-mass potential integration
  warning and returns the integral value anyway.
- `dynamite/mges.py:865-870` logs intrinsic spherical-grid integration
  warnings.
- `orblib_fortran/source/triaxpotent.f90:523-567` prints `dqxgs` integration errors
  but continues.
- `archive/legacy_nnls_fortran/legacy_fortran/mass_helpers/triaxmassbin_f.f90:81-85`
  treats selected integration statuses as warnings in the archived mass-helper
  path.

Impact:

Model outputs can be generated from integrations that exceeded the requested
tolerance. Some warning states may be scientifically acceptable, but the current
pipeline does not consistently carry integration-quality metadata into the
model table or final analysis products.

Recommended fix:

Record integration status and error summaries as model metadata. Require
explicit policy for which statuses are accepted, warning-only, or fatal.

### SNC-002 - High - physical parameter domains are incompletely enforced

Evidence:

- `dynamite/parameter_space.py:133` computes `np.log10(par_value)` for
  logarithmic parameters without first rejecting `par_value <= 0`.
- `dynamite/physical_system.py:1007` has `BarDiskComponent.validate_parset()`
  returning `True` without domain checks.
- `dynamite/physical_system.py:1352-1378` validates and converts
  `GeneralisedNFW` parameters, but allows zero values that later enter
  divisions.
- Earlier audit sections found broken helper methods for `NFW_m200_c` and
  `TriaxialCoredLogPotential` analytical density/mass functions when called.

Impact:

Invalid or boundary physical models can enter later numerical code where they
become `NaN`, `Inf`, divide-by-zero, failed deprojections, or misleading
derived quantities.

Recommended fix:

Centralize parameter validation by component type and require all physically
positive scale, mass, concentration, and dispersion parameters to be finite and
strictly positive before any log transform or backend run.

### SNC-003 - High - solver outputs are not validated as scientific results

Evidence:

- Archived legacy solver process status was not reliably propagated to Python
  (`07_weight_solving.md`, `08_legacy_fortran_backend.md`).
- `dynamite/model_iterator.py:557-558` treats a weights run as successful when
  only `mod.weights[0]` is not `NaN`.
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_CRcut.f90:1139-1145`
  prints non-zero GALAHAD status but does not stop in the archived solver path.
- The local GALAHAD runtime follow-up reached `QPB_solve` in both noCRcut and
  CRcut solver binaries. Both runs logged `QPB_solve exit status = -5`, still
  exited with shell status `0`, and wrote downstream output files.

Impact:

Weights and chi-square values can be accepted without full finite/non-negative
validation, solver convergence validation, and required-output validation. This
is one of the highest-risk scientific correctness issues because orbit weights
are the direct fitted model. The GALAHAD follow-up shows this is not just
theoretical: a solver-level failure can be converted into apparently usable
model files.

Recommended fix:

After every solver run, validate:

- subprocess return code;
- solver-specific convergence/status;
- all weights finite;
- all weights non-negative within tolerance;
- all reported chi-square values finite;
- required output files exist and match expected dimensions.

### SNC-004 - Medium - reproducibility is not fully controlled

Evidence:

- `orblib_fortran/source/unused/orblibprogram.f90:43-54` intentionally used
  stochastic seeds when `random_seed <= 0` in the inactive executable driver.
- `orblib_fortran/Makefile:57-85` and `Makefile.linux:64-92` use
  `-ffast-math` and `-march=native` in the default fast profile.
- `dynamite/coloring.py:745-749` calls `pm.sample()` without an explicit
  random seed.

Impact:

Two runs with the same configuration can differ through random orbit seeds,
backend compiler behavior, or Bayesian sampling. That is acceptable for some
exploration, but not for audits, regression tests, or published reproducibility
claims.

Recommended fix:

Define a reproducible-run mode: positive fixed Fortran seeds, deterministic
Python/PyMC seeds, recorded compiler flags, recorded package versions, and a
non-`fast-math` verification build option.

### SNC-005 - Medium - orbit-library reuse can conflate distinct parameter rows

Evidence:

- `dynamite/model_iterator.py:412` and `468` use `np.allclose()` to decide
  whether a model/orbit-library parameter set already exists.
- `dynamite/model.py:500`, `584`, `628`, and `970` use similar `np.allclose()`
  matching for model lookup and duplicate detection.

Impact:

Close but scientifically distinct parameter values can be treated as the same
model or the same orbit library under default tolerance rules. That risks
reusing the wrong backend outputs.

Recommended fix:

Use exact serialized parameter keys after applying the configured formatting or
a declared per-parameter tolerance policy. Record the key used for each orbit
library.

### SNC-006 - Medium - unit conversions are not covered by focused regression tests

Evidence:

- `dynamite/constants.py` defines global conversions such as `GRAV_CONST_KM`,
  `PARSEC_KM`, `RHO_CRIT`, `ARC_KPC()`, and `ARC_KM()`.
- `dynamite/mges.py` and active `orblib_fortran/` routines independently perform distance,
  arcsec, km, and mass conversions.
- No local unit-test configuration was found that asserts these conversions
  against known values across Python and Fortran paths.

Impact:

Small unit or convention drift can bias masses, radii, or halo quantities and
is hard to detect from end-to-end chi-square tests alone.

Recommended fix:

Add small unit-conversion tests and Python-vs-Fortran parity tests for MGE
projected/intrinsic mass calculations on tiny fixtures.

### SNC-007 - Medium - finite-value validation is incomplete at data boundaries

Evidence:

- Kinematics validation rejects non-positive uncertainties in selected paths
  (`dynamite/kinematics.py:983-988`) but many other data arrays are not checked
  for finite values before normalization or fitting.
- `dynamite/kinematics.py:694` uses `assert` for uniform LOSVD spacing.
- `dynamite/orblib.py:1517-1538` takes `log10` of radius values in log-scaled
  projection tensors without a full finite/positive guard.

Impact:

Input files containing `NaN`, `Inf`, zero radius in log mode, or malformed
LOSVD grids can fail late or propagate invalid values into weights and plots.

Recommended fix:

At every file/data boundary, validate shape, finite values, monotonic grids,
positive uncertainties, and positive radii where log scaling is requested.
Raise `ValueError`, not `assert`.

### SNC-008 - Medium - external chi-square handling can distort totals

Evidence:

- `dynamite/model_iterator.py:184-188` adds returned chi-square values to
  existing table values when reattempting external chi-square.
- `dynamite/model_iterator.py:231-238` returns total chi-square values after
  adding `chi2_ext`.
- `05_model_state_iteration.md` records this as a likely double-counting path.

Impact:

External likelihood terms can be added incorrectly during reattempt workflows,
which changes model ranking.

Recommended fix:

Store base chi-square and external chi-square as separate immutable columns and
compute total chi-square from those columns in one place.

## Overall Assessment

The highest scientific risk is not that the method is unsound; it is that
runtime guardrails are too weak. The priority is to make invalid inputs,
failed backend calls, solver non-convergence, and numerical warnings explicit
in the model table so downstream plots and analysis cannot accidentally treat
questionable outputs as clean results.

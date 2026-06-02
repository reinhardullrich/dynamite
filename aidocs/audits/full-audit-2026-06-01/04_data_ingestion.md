# 04 Data Ingestion

Date started: 2026-06-01

Current-status update, 2026-06-02: this chapter has been adapted for the
`fortran-cleanup` branch. Old sample/test workflows now live under
`archive/dev_tests/`; active local tests for fixture and
configuration behavior live under `tests/`.

## Scope

This audit section covers:

- `dynamite/data.py`
- `dynamite/mges.py`
- `dynamite/kinematics.py`
- `dynamite/populations.py`
- `dynamite/data_prep/`
- ECSV, aperture, binning, MGE, Gauss-Hermite, BayesLOSVD, and population input
  handling

## Evidence Reviewed

- `dynamite/data.py`
- `dynamite/mges.py`
- `dynamite/kinematics.py`
- `dynamite/populations.py`
- `dynamite/data_prep/generate_kin_input.py`
- active fixture inputs under `tests/fixtures/` and archived sample inputs under
  `archive/dev_tests/`
- upstream user documentation references under `docs/getting_started/`

## Findings

### DI-001

Severity: Medium

Area: MGE physical-domain validation

Files:

- `dynamite/mges.py`
- `dynamite/data.py`

Summary:

MGE input validation clips `q > 0.9999`, but it does not explicitly reject
non-positive `q`, non-positive `sigma`, negative/non-finite intensities, or
`inf` values. The generic `Data` reader checks only for `nan`.

Evidence:

```text
data.py:37-43
data_array = np.lib.recfunctions.structured_to_unstructured(
    self.data.as_array())
if np.isnan(data_array).any():
    ...
    raise ValueError(txt)
```

```text
mges.py:35-42
NINES = 0.9999
...
if r['q'] > NINES:
    ...
    r['q'] = NINES
```

The user documentation defines the expected MGE columns:

```text
docs/getting_started/code_overview.rst:80-83
I, sigma, q, PA_twist
```

Impact:

Invalid MGE values can enter mass normalization, deprojection, and projected or
intrinsic mass calculations. `inf` values are especially risky because they are
not `nan` and can propagate silently through numerical integration.

Recommendation:

Validate MGE columns after read:

- required columns: `I`, `sigma`, `q`, `PA_twist`
- all values finite
- `sigma > 0`
- `0 < q <= 1`, with the existing high-q clipping retained if desired
- decide whether `I` must be strictly positive or may be zero

Verification:

Add input tests for missing columns, zero/negative `sigma`, zero/negative `q`,
`q > 1`, `inf`, and `nan`.

### DI-002

Severity: Medium

Area: Raw `KeyError` and incorrect condition in Gauss-Hermite update

Files:

- `dynamite/kinematics.py`

Summary:

`GaussHermite.update_data()` treats `GH_sys_err` as optional in most of the
method, but near the end it unconditionally indexes
`weight_solver_settings['GH_sys_err']`. The condition also checks whether the
literal string `'GH_sys_err'` is contained in the setting value, not whether the
setting exists.

Evidence:

Most of the method treats the key as optional:

```text
kinematics.py:231
if 'GH_sys_err' in weight_solver_settings.keys():
```

```text
kinematics.py:264
if 'GH_sys_err' in weight_solver_settings.keys():
```

But the final condition indexes it unconditionally:

```text
kinematics.py:292-294
if 'GH_sys_err' in weight_solver_settings['GH_sys_err']:
    self.set_default_hist_width()
    self.set_default_hist_bins()
```

Impact:

A Gauss-Hermite configuration without `GH_sys_err` raises a raw `KeyError`
during configuration validation/update. If `GH_sys_err` is present, the final
condition is almost certainly false for normal strings like
`'0.0 0.0 0.0 0.0'`, so the intended refresh behavior does not run.

Recommendation:

Replace the condition with an explicit key check or remove it if histogram
settings do not actually depend on `GH_sys_err`:

```python
if 'GH_sys_err' in weight_solver_settings:
    self.set_default_hist_width()
    self.set_default_hist_bins()
```

Also validate that the string contains at least `number_GH` entries before
indexing.

Verification:

Add tests for Gauss-Hermite configs with no `GH_sys_err`, with exactly
`number_GH` values, and with too few values.

### DI-003

Severity: Medium

Area: Aperture/bin file parsing robustness

Files:

- `dynamite/data.py`
- `dynamite/mges.py`

Summary:

Aperture and bin files are parsed with hand-written line splitting. Blank lines
can crash parsing, and kinematic-bin validation assumes sorted/contiguous bin
IDs by looking at the first and last table rows.

Evidence:

Blank/comment filtering indexes the first non-space character without checking
for empty lines:

```text
data.py:143-145
lines = [line.rstrip('\n').split() for line in open(aperture_fname)
                               if line.lstrip(' ')[0] != '#']
```

```text
data.py:164-166
lines_bins = [line.rstrip('\n').split() for line in open(bin_fname)
                                    if line.lstrip(' ')[0] != '#']
```

The kinematic-bin count assumes the first and last data rows define the ID
range:

```text
data.py:186-190
n_bins_kinem = self.data[-1][0] + (1 if self.data[0][0] == 0 else 0)
if not (n_bins_kinem == len(self.data) == max(grid)):
```

`MGE._bin_grid()` uses similar hand parsing:

```text
mges.py:279-282
bininfo = [line.rstrip('\n').split()
           for line in open(binfile) if line.lstrip(' ')[0] != '#']
```

Impact:

Minor formatting changes in input files can cause raw `IndexError`s. If
kinematic tables are not sorted or use unexpected but explicit bin IDs, error
messages may point to count mismatches rather than the real issue.

Recommendation:

Centralize aperture/bin parsing and validate:

- ignore blank lines safely
- use context managers for files
- parse bin IDs into arrays first
- explicitly require contiguous one-based or zero-based IDs where that is a
  true Fortran contract
- report the exact missing/duplicate IDs

Verification:

Add tests with blank lines, unsorted bin IDs, missing bin IDs, duplicate bin
IDs, and zero/one-based binning variants.

### DI-004

Severity: Medium

Area: BayesLOSVD bin-ID mapping edge case

Files:

- `dynamite/kinematics.py`

Summary:

`BayesLOSVD.map_binID_blosvd_to_binID_dynamite()` intends to map missing
BayesLOSVD bin IDs to zero, but it applies `np.digitize()` and indexes the
sorted mapping before replacing missing values. Missing IDs greater than the
maximum known ID can index past the end of the mapping array.

Evidence:

```text
kinematics.py:1281-1283
idx_missing = np.isin(binID_blosvd, self.data['binID_BayesLOSVD'])
idx_missing = np.where(idx_missing==False)
```

```text
kinematics.py:1286-1292
srt_binid_blosvd = self.data['binID_BayesLOSVD'][idx_srt_binid_blosvd]
srt_binid_dynamite = self.data['binID_dynamite'][idx_srt_binid_blosvd]
index = np.digitize(binID_blosvd, srt_binid_blosvd, right=True)
binID_dynamite = srt_binid_dynamite[index]
# for missing entries, replace with 0
binID_dynamite[idx_missing] = 0
```

Impact:

The intended missing-ID behavior is not reliable. HDF5 files with image pixels
or bins outside the completed BayesLOSVD table can crash aperture/bin-file
generation instead of assigning zero as documented.

Recommendation:

Build the output array initialized to zero, then fill only known IDs through an
explicit dictionary or `np.searchsorted` with bounds checks.

Verification:

Add tests for missing IDs below the minimum, between known IDs, and above the
maximum.

### DI-005

Severity: Medium

Area: BayesLOSVD normalization and finite-value validation

Files:

- `dynamite/kinematics.py`

Summary:

BayesLOSVD ECSV conversion validates that `dlosvd` is positive, but it does not
validate finite LOSVD values or non-zero positive LOSVD sums before normalizing
each aperture.

Evidence:

```text
kinematics.py:983-988
bad_err = np.nonzero(losvd_sigma <= 0)
if len(bad_err[0]) > 0:
    ...
    raise ValueError(txt)
```

```text
kinematics.py:1375-1378
losvd = (self.data['losvd'].T/np.sum(self.data['losvd'], 1)).T
```

Impact:

Rows with zero total LOSVD, negative LOSVD mass, or `inf` values can produce
`nan`/`inf` mean velocities and dispersions. Those derived values are then
stored in the data table and used for histogram defaults and later analysis.

Recommendation:

Validate LOSVD arrays before normalization:

- finite `losvd` and `dlosvd`
- strictly positive `dlosvd`
- positive finite row sums
- decide whether negative LOSVD bins are allowed; if not, reject them

Verification:

Add tests for zero-sum LOSVD rows, negative rows, `inf`, and `nan`.

### DI-006

Severity: Low

Area: `assert` used for user-facing input validation

Files:

- `dynamite/data.py`
- `dynamite/kinematics.py`

Summary:

Several data and kinematics validation checks use `assert`. These are removed
when Python runs with optimization enabled.

Evidence:

```text
data.py:117-119
assert type(sigma) is list
assert type(weight) is list
assert isinstance(datafile, str)
```

```text
kinematics.py:1404-1405
dx = losvd_histograms.dx[0]
assert np.allclose(losvd_histograms.dx, dx), 'vbins must be uniform'
```

Impact:

Some invalid inputs are not rejected under `python -O`. In the LOSVD rebinning
case, non-uniform bins could produce invalid rebinning without the intended
guard.

Recommendation:

Use explicit `if` checks and raise `ValueError` or `TypeError` with clear
messages.

Verification:

Run focused tests with `PYTHONOPTIMIZE=1`.

### DI-007

Severity: Medium

Area: Data-prep package/test drift

Files:

- `dynamite/data_prep/__init__.py`
- `dynamite/data_prep/generate_kin_input.py`
- `archive/dev_tests/test_dataprep.py`

Summary:

The installed `data_prep` package contains only `generate_kin_input.py`, but
Original finding: `archive/dev_tests/test_dataprep.py` imported
`dynamite.data_prep.data_prep_test`. That module was not present, so pytest
collection failed before any data-prep tests could run.

Current status: superseded for the active local baseline. Old `dev_tests`
content is archived under `archive/dev_tests/`; active tests live under
`tests/`.

Evidence:

`dynamite/data_prep/__init__.py` is empty.

```text
archive/dev_tests/test_dataprep.py:7
from dynamite.data_prep import data_prep_test
```

```text
archive/dev_tests/test_dataprep.py:21
from dynamite.data_prep.data_prep_test import data_prep_function_test
```

The pytest collection result is recorded in `00_environment.md`.

Impact:

The data-prep workflow is effectively untested in the current repository state.
Breakages in FITS conversion, aperture/bin generation, or Gauss-Hermite ECSV
writing are unlikely to be caught by CI or local collection.

Recommendation:

Either restore the missing `data_prep_test` module in a dedicated archived-test
revival task or add active tests under `tests/` for the current
`generate_kin_input.py` API.

Verification:

Any active data-prep test added under `tests/` should collect without import
errors.

### DI-008

Severity: Low

Area: Data-prep FITS/file resource handling

Files:

- `dynamite/data_prep/generate_kin_input.py`

Summary:

Data-prep helpers open FITS and text output files directly without context
managers. They also print warnings/status directly rather than using package
logging.

Evidence:

```text
generate_kin_input.py:96
hdu = fits.open(file[0])
```

```text
generate_kin_input.py:105
hdu = fits.open(file[1])
```

```text
generate_kin_input.py:190
aperture_file = open(dir+'aperture'+expr+'.dat', 'w')
```

```text
generate_kin_input.py:208
bins_file = open(dir+'bins'+expr+'.dat', 'w')
```

Direct status output:

```text
generate_kin_input.py:248-249
print('Galaxy: {0}'.format(galaxy))
print(file)
```

Impact:

For normal short scripts this is low risk, but it makes failures less clean and
harder to capture in automated runs. Open FITS handles can linger after
exceptions.

Recommendation:

Use `with fits.open(...) as hdu:` and `with open(...) as f:`. Route status and
warnings through logging so batch runs and tests can capture them.

Verification:

Add a smoke test that creates aperture/bin/kinematics files in a temp directory
and verifies no warnings or open-handle leaks on normal execution.

## Positive Observations

- Generic ECSV loading rejects `nan` values early for numeric tables.
- Integrated data validates PSF weights sum to one.
- Gauss-Hermite uncertainty columns are checked for zero or negative values
  after systematic errors are applied.
- BayesLOSVD conversion records velocity metadata (`dv`, `vcent`, `nbins`,
  `nvbins`) needed by the weight solver.
- The package has explicit user-facing conversion helpers for legacy MGE,
  Gauss-Hermite, and BayesLOSVD inputs.

## Open Questions

- Should MGE intensity `I` be required to be strictly positive, or are zero
  components valid in supported workflows?
- Is `GH_sys_err` mandatory for every Gauss-Hermite run, or only when
  `number_GH` exceeds the observed maximum order?
- Should BayesLOSVD negative LOSVD bins be rejected, clipped, or allowed as
  statistical artifacts?

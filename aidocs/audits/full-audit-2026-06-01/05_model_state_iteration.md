# 05 Model State And Iteration

Date started: 2026-06-01

## Scope

This audit section covers:

- `dynamite/model.py`
- `dynamite/model_iterator.py`
- `all_models.ecsv` creation, loading, mutation, and saving
- model directory assignment
- resume and failure reattempt behavior
- multiprocessing boundaries in model iteration

## Evidence Reviewed

- `dynamite/model.py`
- `dynamite/model_iterator.py`
- `dynamite/config_reader.py`

## Findings

### MS-001

Severity: High

Area: External chi-square table update

Files:

- `dynamite/model_iterator.py`

Summary:

When a system has a `Chi2Ext` component, `write_output_to_all_models_table()`
writes `chi2_ext` to the entire `chi2_ext_added` column instead of the current
row.

Evidence:

```text
model_iterator.py:612-617
for i, row in enumerate(rows_to_do):
    if self.has_chi2_ext:
        orb_done, wts_done, chi2, kinchi2, kinmapchi2, chi2_ext, \
            all_done, time = output[i]
        self.all_models.table['chi2_ext_added'] = chi2_ext
```

The other fields are row-specific:

```text
model_iterator.py:620-626
self.all_models.table['orblib_done'][row] = orb_done
...
self.all_models.table['time_modified'][row] = time
```

Impact:

Every model row can receive the last processed external chi-square value. This
corrupts `all_models.ecsv` for external-chi-square workflows, affects best-model
selection, and can hide which rows actually had external chi-square calculated.

Recommendation:

Write the row-specific cell:

```python
self.all_models.table['chi2_ext_added'][row] = chi2_ext
```

Verification:

Add a test with two models and a deterministic `Chi2Ext` component returning
different values per row. Assert that each row keeps its own
`chi2_ext_added`.

### MS-002

Severity: High

Area: Float tolerance used as model identity

Files:

- `dynamite/model.py`
- `dynamite/model_iterator.py`

Summary:

Model identity and orbit-library reuse are based on `np.allclose()` comparisons
of parameter rows. The default tolerance can treat distinct nearby grid points
as the same model or same orbit library.

Evidence:

```text
model_iterator.py:409-413
all_data = self.all_models.table[self.orblib_parameters]
...
if any(np.allclose(tuple(row_data), tuple(r)) for r in previous_data):
```

```text
model_iterator.py:464-469
orblib_data = self.all_models.table[self.orblib_parameters]
...
if np.allclose(tuple(row_data), tuple(orblib)):
```

```text
model.py:499-501
for idx, row in enumerate(self.table[self.config.parspace.par_names]):
    if np.allclose(tuple(parset), tuple(row)):
```

```text
model.py:581-584
row_comp = tuple(model.parset[self.config.parspace.par_names])
...
if np.allclose(row_comp, tuple(row)):
```

```text
model.py:626-629
for row_id, row in enumerate(self.table[orblib_parameters][:model_id+1]):
    if np.allclose(row_comp, tuple(row)):
```

Impact:

If parameter-grid spacing is small relative to NumPy's default `allclose`
tolerance, distinct models can be deduplicated, assigned to the wrong existing
directory, or have velocity-scaling factors derived from the wrong original
orbit library.

Recommendation:

Use exact identity for stored table parameters after canonical formatting, or
define a project-specific tolerance tied to parameter `minstep`/`sformat` and
document it. A robust option is to generate a canonical parameter key from the
raw parameter values used by the generator.

Verification:

Add tests with two parameter rows separated by less than default `np.allclose`
tolerance but intended to be distinct. Assert that they get distinct model rows
or orbit libraries when required.

### MS-003

Severity: Medium

Area: `Chi2Ext` reattempt arithmetic

Files:

- `dynamite/model_iterator.py`

Summary:

During `reattempt_failed_weights()`, external chi-square reattempt output is
added to the existing table values, but `get_missing_chi2_ext()` already returns
the full chi-square values after adding external chi-square to the weight-file
values.

Evidence:

`get_missing_chi2_ext()` constructs full values:

```text
model_iterator.py:229-236
_ = mod.get_weights(orblib)
...
mod.chi2 += chi2_ext
mod.kinchi2 += chi2_ext
mod.kinmapchi2 += chi2_ext
mod.chi2_ext = chi2_ext
```

The caller then adds those returned full values to existing table values:

```text
model_iterator.py:183-189
chi2, kinchi2, kinmapchi2, chi2_ext, time = output[i]
all_models.table[row]['chi2'] += chi2
all_models.table[row]['kinchi2'] += kinchi2
all_models.table[row]['kinmapchi2'] += kinmapchi2
all_models.table[row]['chi2_ext_added'] = chi2_ext
```

Impact:

External chi-square reattempts can double count existing chi-square values. If
the row already has base weight-solver chi-square values, adding a full returned
value makes the table too large by approximately the base chi-square.

Recommendation:

Either return only the external increment from `get_missing_chi2_ext()` and add
it in the caller, or return full values and assign them in the caller. Do not
mix both patterns.

Verification:

Add a test with known base chi-square and known external chi-square. Reattempt
should produce `base + external`, not `base + base + external`.

### MS-004

Severity: Medium

Area: Failure handling in multiprocessing runs

Files:

- `dynamite/model_iterator.py`

Summary:

`create_and_run_model()` catches only `RuntimeError` from model execution. Other
exceptions from directory setup, orbit-library creation, weight solving,
external chi-square, or file reads propagate through `Pool.map()` and can abort
the whole iteration before table status is written.

Evidence:

```text
model_iterator.py:550-558
cwd = os.getcwd()
try:
    orblib = mod.get_orblib()
    ...
    _ = mod.get_weights(orblib)
```

```text
model_iterator.py:574-586
except RuntimeError:
    os.chdir(cwd)
    mod.chi2, mod.kinchi2, mod.kinmapchi2 = np.nan, np.nan, np.nan
    ...
    self.logger.warning(w_txt)
```

Impact:

A single `ValueError`, `FileNotFoundError`, `KeyError`, `OSError`, or solver
exception can prevent the remaining outputs from being written back to
`all_models.ecsv`. This makes resume behavior less reliable and can leave newly
assigned directories in the table without updated status.

Recommendation:

Catch a broader exception at the model-task boundary, record the exception type
and message, return a failed model status, and let the iteration continue.
Avoid swallowing exceptions silently: preserve tracebacks in logs or per-model
failure files.

Verification:

Inject controlled `ValueError` and `FileNotFoundError` failures in one worker
and assert that other models finish and the failed row is saved with explicit
failed status.

### MS-005

Severity: Medium

Area: Atomicity of `all_models.ecsv`

Files:

- `dynamite/model.py`
- `dynamite/model_iterator.py`

Summary:

`AllModels.save()` writes directly to the final `all_models.ecsv` path with
`overwrite=True`. Iteration relies on this file for resume behavior, but writes
are not atomic and there is no backup or temporary-file rename.

Evidence:

```text
model.py:678-683
def save(self):
    self.table.write(self.filename, format='ascii.ecsv', overwrite=True)
```

The iterator saves at several important checkpoints:

```text
model_iterator.py:320-321
self.par_generator.generate(current_models=self.all_models)
self.all_models.save()
```

```text
model_iterator.py:341-343
# save all_models here - as it is useful to have directories saved
self.all_models.save()
```

```text
model_iterator.py:388
self.all_models.save()
```

Impact:

An interruption during write can corrupt the main state file. Since the file is
the main resume ledger, a partial write can block recovery even if model
directories contain useful outputs.

Recommendation:

Write to a temporary file in the same directory, fsync if practical, then use an
atomic replace. Optionally keep a `.bak` copy of the last known-good table.

Verification:

Add a test around a temporary output directory that simulates a write failure
and asserts the previous table remains readable.

### MS-006

Severity: Medium

Area: Configuration constructor mutates model-state files

Files:

- `dynamite/config_reader.py`
- `dynamite/model.py`

Summary:

Model state reconciliation is invoked during `Configuration` construction,
including indicator-file updates, table writes, and possible directory
deletion. This finding cross-references CR-001 because it directly affects
model-state safety.

Evidence:

```text
config_reader.py:564-576
self.all_models = model.AllModels(config=self)
...
self.all_models.update_orblib_flags(d)
self.all_models.update_model_table()
```

`update_model_table()` can delete incomplete rows and directories:

```text
model.py:139-141
the model will be deleted from the table and the model directory will
be deleted, too.
```

```text
model.py:262
shutil.rmtree(directory)
```

Impact:

Read-only workflows such as plotting, analysis, audit, or config inspection can
modify or delete model-state artifacts.

Recommendation:

Add read-only configuration construction and make reconciliation/deletion an
explicit operation with a dry-run mode.

Verification:

Create a fixture `all_models.ecsv` plus incomplete directories and assert that
read-only construction leaves them unchanged.

### MS-007

Severity: Low

Area: Mutable default arguments

Files:

- `dynamite/model_iterator.py`

Summary:

`ModelIterator.__init__()` and `assign_model_directories()` use mutable default
arguments. This is also noted in CR-003, but it is relevant here because these
methods manage iteration state and row assignment.

Evidence:

```text
model_iterator.py:35-38
def __init__(self,
             config=None,
             model_kwargs={},
```

```text
model_iterator.py:421
def assign_model_directories(self, rows_orblib=[], rows_ml=[]):
```

Impact:

The current code does not obviously mutate these defaults directly, so this is
low immediate risk. It remains fragile for future iteration changes.

Recommendation:

Use `None` defaults and allocate local lists/dicts inside the method.

Verification:

Add a regression test that calls directory assignment multiple times without
explicit arguments and verifies no state leaks between calls.

## Positive Observations

- The iterator saves `all_models.ecsv` after parameter generation and after
  directory assignment, which improves crash recovery compared with saving only
  after model completion.
- Orbit-library and weight-solving phases can be split, reducing concurrent
  writes into shared orbit-library directories.
- Existing orbit libraries are reused across different `ml` values, which is
  important for performance.
- Failed weight-solving reattempt logic exists and is configurable through
  `reattempt_failures`.

## Open Questions

- What exact numeric tolerance should define model identity, if any?
- Should `all_models.ecsv` include an explicit failure-reason column rather than
  encoding failures only as `nan` chi-square/status flags?
- Should model-state reconciliation be opt-in by default for analysis and
  plotting workflows?

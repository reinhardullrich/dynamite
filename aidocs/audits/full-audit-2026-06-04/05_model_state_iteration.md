# 05 Model State And Iteration

Audit date: 2026-06-04

## Scope

`all_models.ecsv`, model directories, resume/repair behavior, pruning,
external chi-square, and model/orbit-library identity.

## Findings

### MS-001 - `all_models.ecsv` writes are not atomic

Severity: High.

Evidence:

- `AllModels.save()` writes directly to `self.filename` with
  `format='ascii.ecsv', overwrite=True`.
- conversion and best-model table writes also use direct final-path writes.

Impact: interruption during write can corrupt the model table.

Recommendation: write to a temporary sibling file, fsync if needed, validate
readback, then `os.replace()`.

### MS-002 - Configuration startup can repair/prune model state

Severity: High.

Evidence:

- `Configuration.__init__()` calls `update_orblib_flags()` and
  `update_model_table()`.
- `update_model_table()` can mark rows complete, add external chi-square,
  delete rows, remove orbit-library directories, and save the table.

Recommendation: separate read-only inspection from explicit `repair_state()` or
`resume_state()` workflows.

### MS-003 - Recursive model/orbit-library deletion is broad

Severity: Medium/High.

Evidence:

- failed/incomplete model cleanup can call `shutil.rmtree()` on orbit-library
  directories.
- pruning can delete either whole orbit-library directories or model `ml`
  directories.

Recommendation: add dry-run, explicit affected path list, and recovery/trash
mode for human-run cleanup.

### MS-004 - External chi-square handling remains fragile

Severity: Medium/High.

Evidence:

- `update_model_table()` adds `chi2_ext` into `chi2`, `kinchi2`, and
  `kinmapchi2` when `chi2_ext_added` is NaN and weights are done.
- retry/resume behavior depends on the state of `chi2_ext_added`.

Impact: interrupted or partially updated tables can produce confusing totals.

Recommendation: store base chi-square and external chi-square separately, then
derive totals or update atomically in one operation.

### MS-005 - Model/orbit-library identity uses `np.allclose()`

Severity: Medium/High.

Evidence:

- model lookup, row lookup, orbit-library reuse, pruning, and external
  chi-square duplicate logic use `np.allclose()`.

Recommendation: add explicit stable keys with documented precision and include
those keys in `all_models.ecsv`.

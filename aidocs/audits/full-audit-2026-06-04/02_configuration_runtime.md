# 02 Configuration Runtime

Audit date: 2026-06-04

## Scope

Configuration parsing, runtime startup, output mutation, validation, logging,
and cleanup helpers.

## Findings

### CR-001 - Configuration construction can delete output state

Severity: High.

Evidence:

- `Configuration.__init__(..., reset_existing_output=True)` deletes the
  configured output directory tree with `shutil.rmtree()`.
- This is explicit, but it is still attached to object construction.

Impact: callers that only expect parsing can accidentally run destructive
setup.

Recommendation: split read-only parse/validate from destructive reset/setup.
Keep destructive behavior behind an explicit workflow command or method.

### CR-002 - Configuration construction mutates model state

Severity: High.

Evidence:

- `Configuration.__init__()` instantiates `AllModels`.
- It scans model directories, calls `update_orblib_flags()`, and then
  `update_model_table()`.
- `update_model_table()` can delete rows/directories and save
  `all_models.ecsv`.

Impact: merely opening a config can repair, prune, or rewrite runtime state.

Recommendation: make state repair explicit. Provide a read-only config mode
that never writes or deletes.

### CR-003 - Cleanup helpers are broad and recursive

Severity: Medium/High.

Evidence:

- `remove_existing_orblibs()` removes the whole model output tree.
- `remove_existing_orbital_weights()` removes all `ml*` directories.
- `remove_existing_plots(remove_directory=True)` removes the plot tree.
- `remove_existing_all_models_file(wipe_other_files=True)` removes regular
  files in the output directory.

Recommendation: add dry-run/report modes and require explicit confirmation in
human-run workflows before recursive cleanup.

### CR-004 - Validation is not cleanly separated by responsibility

Severity: Medium.

- some validation messages still say "Legacy mode";
- physical/domain validation is not centralized;
- several errors are discovered only after configuration objects and runtime
  paths are partly initialized.

Recommendation: separate schema validation, physical-domain validation, and
runtime-readiness validation.

### CR-005 - Logging reset is global

Severity: Low/Medium.

`Configuration(reset_logging=True)` resets DYNAMITE logging globally. This is
convenient for scripts but not ideal for embedding or tests.

Recommendation: prefer caller-provided loggers or scoped logging setup in new
APIs.

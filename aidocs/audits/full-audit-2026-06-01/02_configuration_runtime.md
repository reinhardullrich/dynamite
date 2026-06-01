# 02 Configuration Runtime

Date started: 2026-06-01

## Scope

This audit section covers:

- `dynamite/config_reader.py`
- configuration parsing and validation
- output directory creation
- constructor side effects
- interaction with `AllModels`
- runtime/bootstrap mutation of model state
- mutable defaults visible in runtime-facing classes

## Evidence Reviewed

- `dynamite/config_reader.py`
- `dynamite/model.py`
- `dynamite/model_iterator.py`
- `dynamite/physical_system.py`
- `dynamite/parameter_space.py`
- sample configs under `dev_tests/` and upstream `docs/tutorial_notebooks/`

## Findings

### CR-001

Severity: High

Area: Configuration constructor side effects / data deletion

Files:

- `dynamite/config_reader.py`
- `dynamite/model.py`

Summary:

Constructing `Configuration` can mutate or delete model output state before any
explicit model run starts. The constructor creates output directories, updates
orbit-library indicator files, calls `AllModels.update_model_table()`, and that
method can delete incomplete model rows and remove model directories.

Evidence:

`Configuration.__init__` creates directories and optionally removes the output
tree:

```text
config_reader.py:247-251
if reset_existing_output:
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
self.make_output_directory_tree()
```

Later in the same constructor:

```text
config_reader.py:574-576
for d in directories:
    self.all_models.update_orblib_flags(d)
self.all_models.update_model_table()
```

`AllModels.update_model_table()` states and implements deletion of incomplete
models:

```text
model.py:139-141
If no orblib exists on disk and the weights are not available either,
the model will be deleted from the table and the model directory will
be deleted, too.
```

and:

```text
model.py:261-263
shutil.rmtree(directory)
```

Impact:

A user or script that only intends to inspect a config can modify
`all_models.ecsv`, touch status files, or delete incomplete output directories.
This is especially risky for audit, plotting, analysis, or debugging workflows
that need read-only access to existing runs.

Recommendation:

Separate config parsing from output-state reconciliation. Add an explicit
mode/argument for state mutation, for example:

- `Configuration(..., reconcile_output_state=True)` defaulting to current
  behavior only if backward compatibility requires it.
- `Configuration(..., read_only=True)` that refuses all output writes/deletes.
- Move deletion into an explicit maintenance method with a dry-run option.

Verification:

Create a fixture output directory with an incomplete `all_models.ecsv` row and
assert that read-only config construction does not change files or directories.

### CR-002

Severity: Medium

Area: Destructive reset API

Files:

- `dynamite/config_reader.py`

Summary:

`Configuration(reset_existing_output=True)` recursively removes the configured
output directory. The operation is documented in the docstring, but it is still
a high-impact behavior on an object constructor.

Evidence:

```text
config_reader.py:247-250
if reset_existing_output:
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
```

Impact:

Accidental use of `reset_existing_output=True` can delete model outputs and
large orbit libraries. Because this happens during object construction, it is
easy to trigger indirectly from test scripts or notebooks.

Recommendation:

Add stronger safeguards before recursive deletion:

- require `output_directory` to be inside an expected workspace
- log an explicit warning with the absolute path
- support dry-run
- consider requiring a second explicit flag such as
  `confirm_delete_output=True`

Verification:

Unit-test that reset refuses dangerous paths and logs the absolute deletion
target.

### CR-003

Severity: Medium

Area: Mutable default arguments

Files:

- `dynamite/physical_system.py`
- `dynamite/parameter_space.py`
- `dynamite/model_iterator.py`

Summary:

Several runtime-facing constructors and methods use mutable default arguments.
This is a Python correctness risk because defaults are shared across calls.

Evidence:

Examples:

```text
physical_system.py:389-391
kinematic_data=[]
population_data=[]
parameters=[]
```

```text
parameter_space.py:367-369
def __init__(self, par_space=[], parspace_settings=None, name=None)
```

```text
parameter_space.py:410-412
def generate(..., kw_specific_generate_method={})
```

```text
model_iterator.py:35-37
def __init__(..., model_kwargs={})
```

```text
model_iterator.py:421
def assign_model_directories(self, rows_orblib=[], rows_ml=[])
```

Impact:

If any method mutates one of these default objects, state can leak between
instances or calls. Some of these defaults may not currently be mutated, but
the pattern is risky and makes future changes fragile.

Recommendation:

Replace mutable defaults with `None` and allocate inside the function:

```python
if rows_orblib is None:
    rows_orblib = []
```

Prioritize constructors on shared domain objects such as `Component` and
`ParameterGenerator`.

Verification:

Add tests that instantiate multiple objects without explicit lists and assert
that their list attributes are distinct objects.

### CR-004

Severity: Medium

Area: Validation robustness

Files:

- `dynamite/config_reader.py`
- `dynamite/weight_solvers.py`
- sample YAML configs

Summary:

`Settings.validate()` unconditionally indexes
`weight_solver_settings['nnls_solver']`. The documentation and sample legacy
configs include `nnls_solver: 1` even for `LegacyWeightSolver`, but if a legacy
config omits this otherwise irrelevant setting, validation will raise a raw
`KeyError`.

Evidence:

```text
config_reader.py:85
if self.weight_solver_settings['nnls_solver'] == 'cvxopt' ...
```

Docs indicate the setting is type-dependent:

```text
type = LegacyWeightSolver then set nnls_solver : 1
type = NNLS then nnls_solver can be one of the strings ...
```

Impact:

Config errors are less clear than necessary, and a setting that only matters
for solver selection is required even when the legacy solver path does not use
the Python NNLS backend in the same way.

Recommendation:

Validate `nnls_solver` conditionally by `weight_solver_settings['type']`.
For example:

- require `nnls_solver in {'scipy', 'cvxopt'}` for `type: NNLS`
- accept or default legacy `nnls_solver` only for `LegacyWeightSolver`
- raise clear `ValueError` for unknown solver types/settings

Verification:

Add config validation tests for:

- `LegacyWeightSolver` without `nnls_solver`
- `LegacyWeightSolver` with `nnls_solver: 1`
- `NNLS` with `scipy`
- `NNLS` with `cvxopt` missing
- unknown solver type

### CR-005

Severity: Low

Area: Exception hygiene

Files:

- `dynamite/config_reader.py`
- `dynamite/model.py`
- `dynamite/parameter_space.py`
- `dynamite/model_iterator.py`

Summary:

Several code paths use broad bare `except:` blocks. Some re-raise immediately,
but others swallow the original exception and continue with a warning.

Evidence:

Examples found around:

- config file open and IO path handling in `config_reader.py`
- model directory cleanup in `model.py`
- parameter-generator settings extraction in `parameter_space.py`
- plotting failure handling in `model_iterator.py`

Impact:

Broad exception handling can hide programming errors, keyboard interrupts, and
unexpected state corruption. In cleanup paths it may also report a benign
warning while failing to delete or reconcile the intended state.

Recommendation:

Replace bare `except:` with targeted exception types. Where the code is
intentionally best-effort, log the exception details with `exc_info=True`.

Verification:

Run tests with injected filesystem and config failures and confirm the logged
errors preserve root-cause exceptions.

## Positive Observations

- YAML parsing uses `UniqueKeyLoader`, which rejects duplicate YAML keys.
- Top-level unknown configuration keys are rejected.
- `io_settings` requires the exact expected keys: `input_directory`,
  `output_directory`, and `all_models_file`.
- Component config entries are checked against allowed keys before further
  component setup.
- The code normalizes input/output paths by adding trailing slashes.

## Open Questions

- Should there be a supported read-only mode for plotting/audit workflows?
- Should model-table repair and deletion ever happen automatically during
  `Configuration` construction?
- Which existing scripts depend on constructor-time cleanup?
- Should legacy solver configs be allowed to omit `nnls_solver`?

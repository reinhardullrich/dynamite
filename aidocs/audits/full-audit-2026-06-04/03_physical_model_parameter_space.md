# 03 Physical Model And Parameter Space

Audit date: 2026-06-04

## Scope

Physical system components, parameters, parameter transforms, parameter-space
generation, and model identity.

## Findings

### PM-001 - Logarithmic parameter domains are not centrally guarded

Severity: High.

Evidence:

- `Parameter.get_par_value_from_raw_value()` returns `10.**raw_value`.
- `Parameter.get_raw_value_from_par_value()` returns `np.log10(par_value)`.
- There is no central finite/positive check before `np.log10()`.
- `System.validate_parset()` explicitly skips negative checks for logarithmic
  parameters.

Impact: invalid raw or physical values can propagate until numerical code sees
  infinities, NaNs, or nonphysical parameters.

Recommendation: add explicit finite/positive validators for logarithmic
parameters before conversion and before backend launch.

### PM-002 - Tolerance-based model identity can conflate distinct models

Severity: Medium/High.

Evidence:

- `ParameterGenerator._is_newmodel()` uses `np.allclose(..., rtol=1e-6)`.
- `AllModels.get_model_from_parset()`, `get_row_from_model()`,
  `get_ml_of_original_orblib()`, pruning, and chi-square duplicate logic also
  use `np.allclose()`.

Impact: close but intentionally distinct model rows can be treated as the same
model or orbit library.

Recommendation: introduce stable `model_key` and `orblib_key` values generated
from normalized parameter values and explicit precision rules.

### PM-003 - Some physical-system accessors use `assert`

Severity: Medium.

Evidence:

- `System.get_component_from_name()` uses `assert len(idx[0]) == 1`.

Impact: `assert` is disabled under optimized Python and should not enforce
runtime scientific correctness.

Recommendation: replace runtime `assert` validation with explicit
`ValueError`/`RuntimeError`.

### PM-004 - Dark-halo and barred-model validation remains incomplete for active direct backend

Severity: Medium.

- detailed physical-domain checks for halo parameters are not centralized;
- barred/rotating paths lack current regression fixtures.

Recommendation: add component-level finite/domain validators and a dedicated
rotating-frame fixture before treating `Omega != 0` behavior as verified.

### PM-005 - SpecificModels intentionally bypasses normal grid controls

Severity: Low/Medium.

`SpecificModels` ignores `lo`, `hi`, `step`, `minstep`, `fixed`, and stopping
criteria. This is useful for exact model lists but easy to misuse.

Recommendation: validate `specific_values` through the same physical-domain
checks used for generated models.

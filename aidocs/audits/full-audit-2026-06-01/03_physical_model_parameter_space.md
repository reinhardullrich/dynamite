# 03 Physical Model And Parameter Space

Date started: 2026-06-01

## Scope

This audit section covers:

- `dynamite/physical_system.py`
- `dynamite/parameter_space.py`
- physical component validation
- component and parameter lookup behavior
- parameter value/raw-value transforms
- parameter-space bounds checks
- dark-halo helper methods exposed by the physical model layer

## Evidence Reviewed

- `dynamite/physical_system.py`
- `dynamite/parameter_space.py`
- local import and compile checks from `00_environment.md`

## Findings

### PM-001

Severity: Medium

Area: Duplicate component-name validation

Files:

- `dynamite/physical_system.py`

Summary:

`System.validate()` claims to reject duplicate component names, but it checks
object identity rather than component names. Two distinct component objects with
the same `.name` pass this check.

Evidence:

```text
physical_system.py:53-54
Ensures the System has the required attributes: at least one component,
no duplicate component names
```

```text
physical_system.py:69-70
if len(self.cmp_list) != len(set(self.cmp_list)):
    raise ValueError('No duplicate component names allowed')
```

Impact:

Duplicate component names can flow into parameter naming and later lookup code.
That can make `get_component_from_name()`, parameter suffix parsing, and output
naming fail late or behave ambiguously.

Recommendation:

Validate names explicitly:

```python
names = [cmp.name for cmp in self.cmp_list]
if len(names) != len(set(names)):
    raise ValueError("No duplicate component names allowed")
```

Verification:

Add a unit test that constructs two components with the same `name` and asserts
that `System.validate()` raises before any parameter-space construction.

### PM-002

Severity: Medium

Area: Runtime validation depends on `assert`

Files:

- `dynamite/physical_system.py`
- `dynamite/parameter_space.py`

Summary:

Component and parameter lookup uniqueness checks use `assert`. Python removes
assertions when run with optimization (`python -O`), so these runtime checks can
disappear.

Evidence:

```text
physical_system.py:168-172
idx = np.where(cmp_list_list == cmp_name)
...
assert len(idx[0]) == 1, error_msg
```

```text
parameter_space.py:226-230
idx = np.where(name_array == name)
...
assert len(idx[0]) == 1, error_msg
```

Impact:

Under optimized Python, zero or multiple matches no longer raise the intended
error. Code then indexes `idx[0][0]`, which can raise a less clear error for no
matches or silently take the first match when duplicates exist.

Recommendation:

Replace runtime `assert` validation with explicit `if` checks that raise
`ValueError` or a domain-specific exception.

Verification:

Run focused tests both normally and with `PYTHONOPTIMIZE=1` to prove duplicate
or missing names still fail deterministically.

### PM-003

Severity: High

Area: Logarithmic parameter domain validation

Files:

- `dynamite/physical_system.py`
- `dynamite/parameter_space.py`

Summary:

Logarithmic parameters are skipped by the generic non-negative validation, and
`Parameter.get_raw_value_from_par_value()` calls `np.log10(par_value)` without
checking that `par_value > 0`.

Evidence:

```text
physical_system.py:112
non-negative, except for logarithmic parameters which are not checked.
```

```text
physical_system.py:126-128
p_raw_values = [par[p.name]
                for p in self.parameters if not p.logarithmic]
isvalid = np.all(np.sign(p_raw_values) >= 0)
```

```text
physical_system.py:475-477
p_raw_values = [par[self.get_parname(p.name)]
            for p in self.parameters if not p.logarithmic]
isvalid = np.all(np.sign(p_raw_values) >= 0)
```

```text
parameter_space.py:132-134
if self.logarithmic is True:
    raw_value = np.log10(par_value)
```

Impact:

Non-positive physical values for logarithmic parameters can become `nan`,
`-inf`, or invalid physical states. The generic validation layer does not catch
this before parameter generation, file writing, or model execution.

Recommendation:

For logarithmic parameters, validate physical parameter values before converting
to raw values. At minimum, reject `par_value <= 0` with a clear `ValueError`.
For raw log values, validate finite values with `np.isfinite()`.

Verification:

Add tests for zero, negative, `nan`, and `inf` logarithmic parameter values in
both direct `Parameter` conversion and `ParameterSpace.validate_parspace()`.

### PM-004

Severity: Medium

Area: Barred-system parameter validation

Files:

- `dynamite/physical_system.py`

Summary:

`BarDiskComponent.validate_parset()` returns `True` unconditionally. The comment
says validation is skipped because the angles are known, but the method accepts
the parameter dictionary and does not validate finite values, angle ranges, or
consistency with the expected `theta`, `psi`, and `phi` parameters.

Evidence:

```text
physical_system.py:1005
self.par = ['theta', 'psi', 'phi']
```

```text
physical_system.py:1007-1009
def validate_parset(self, par):
    # Skip validation as we already know the angles
    return True
```

Impact:

Invalid or non-finite bar angles can pass parameter-space validation and fail
later at Fortran input generation, orbit integration, or scientific analysis.

Recommendation:

Validate that all required angle keys are present, finite, and inside the
accepted domain. If the accepted domain is intentionally broad, document that
explicitly and still reject `nan`/`inf`.

Verification:

Add tests with missing angle keys, `nan`, `inf`, and out-of-domain angle values.

### PM-005

Severity: High

Area: Analytical dark-halo helper methods

Files:

- `dynamite/physical_system.py`

Summary:

Several analytical dark-halo helper methods appear broken if called directly.
`NFW_m200_c` helper methods reference names that are not imported or not bound
as instance/static methods. `TriaxialCoredLogPotential` unpacks parameters in a
different order from its declared legacy parameter order and references
undefined `G`.

Evidence:

`NFW_m200_c` defines helper functions without `self` or `@staticmethod` and
uses unqualified names:

```text
physical_system.py:1233-1238
def rhoc(c,f):
    return 200/3 * rhocrit * c**3 / (log(1 + c) - c/(1+c))
def rc(c,f):
    return (3*M200(c,f)/(800*pi*rhocrit*c**3))**(1/3)
def M200(c,f):
    return 800*pi/3*rhocrit*(rc*c)**3
```

```text
physical_system.py:1240-1247
def potential(x, y, z, pars):
    c, f = pars
    ...
    prefactor = 4*pi*G*rhoc(c,f)*(rc(c,f)**3)/sqrt(d2)
```

`TriaxialCoredLogPotential` declares one parameter order but unpacks another:

```text
physical_system.py:1302
par_names = ['Vc', 'Rc', 'p', 'q']
```

```text
physical_system.py:1311-1313
def potential(x, y, z, pars):
    rc, vc, p, q = pars
```

It also references undefined `G`:

```text
physical_system.py:1317-1320
rho = vc**2/(4*np.pi*G*(m+rc**2)**2)*...
```

```text
physical_system.py:1324-1332
Menc = r*vc**2/G * ...
```

Impact:

If these public helper methods are used by tests, notebooks, future Python
orbit calculations, or scientific validation scripts, they can raise
`NameError`, use swapped `Vc`/`Rc` values, or return physically incorrect
results. The legacy Fortran path may not call these helpers today, which makes
the risk easy to miss in normal model runs.

Recommendation:

Decide whether these methods are supported public APIs or dead code.

If supported:

- add `@staticmethod` consistently or add `self`
- use `np.log`, `np.pi`, `np.sqrt`, and `dyn.constants` explicitly
- bind helper calls through the class name or static methods
- align `TriaxialCoredLogPotential` unpacking with `par_names`
- add finite/domain checks and numerical tests

If unsupported:

- remove or mark them private/experimental
- keep the legacy Fortran handoff methods as the supported path

Verification:

Add direct tests for each dark-halo `potential`, `density`, and
`mass_enclosed` helper on simple finite inputs.

### PM-006

Severity: Medium

Area: Generalised NFW domain checks

Files:

- `dynamite/physical_system.py`

Summary:

`GeneralisedNFW.validate_parset()` allows `c == 0` and `Mvir == 0`, despite its
docstring saying `c` and `Mvir` must be positive. It also does not check that
values are finite.

Evidence:

```text
physical_system.py:1356
Requires c and Mvir >0, and gam leq 1
```

```text
physical_system.py:1370
if (par['c']<0.) or (par['Mvir']<0.) or (par['gam']>1):
```

`convert_parset()` later divides by `c`:

```text
physical_system.py:1393-1394
r200 = (3 * Mvir / (800 * np.pi * rho_crit))**(1.0 / 3.0)
rc = r200 / c
```

Impact:

Zero or non-finite values can pass validation and then produce division by
zero, `nan`, or `inf` during potential, density, mass, or acceleration
calculation.

Recommendation:

Use strict positive checks for `c` and `Mvir`, finite checks for all three
parameters, and an explicit lower/upper domain for `gam` based on the supported
formula.

Verification:

Add tests for `c=0`, `Mvir=0`, negative values, `nan`, `inf`, and edge values
of `gam`.

### PM-007

Severity: Low

Area: Class-level parameter schema state

Files:

- `dynamite/parameter_space.py`

Summary:

`Parameter.attributes` is class-level state that is overwritten in every
`Parameter.__init__()`. The current constructor always sets the same keys, so
this is not an immediate runtime failure, but it makes the schema global and
fragile if subclasses or future constructor options are added.

Evidence:

```text
parameter_space.py:32
attributes = []
```

```text
parameter_space.py:50
self.__class__.attributes = list(self.__dict__.keys())
```

```text
parameter_space.py:55-60
if k not in self.__class__.attributes:
    ...
    raise ValueError(text)
```

Impact:

Future subclassing or optional attributes can unexpectedly change validation
for all instances of the same class.

Recommendation:

Use an explicit immutable class constant for allowed attributes, or validate
against instance-level keys when that is the intended behavior.

Verification:

Add a test that creates multiple `Parameter` instances and verifies that
allowed update keys do not depend on creation order.

## Positive Observations

- Triaxial visible components validate deprojection by converting `(p, q, u)`
  to viewing angles and rejecting `nan` results.
- `System.get_component_from_class()` uses explicit `ValueError` rather than
  `assert` and correctly rejects zero or multiple matches.
- `ParameterSpace.validate_parspace()` checks component validation before bound
  checks, which gives domain-specific code a chance to reject invalid physical
  states.
- Parameter-space bounds are checked against `lo` and `hi` when those settings
  are present.

## Open Questions

- Are the analytical dark-halo helper methods considered supported API, or are
  they legacy/dead code retained for reference?
- Should logarithmic parameters be validated in physical units everywhere, or
  only at conversion boundaries?
- What angle ranges are physically and operationally valid for barred-system
  `theta`, `psi`, and `phi`?

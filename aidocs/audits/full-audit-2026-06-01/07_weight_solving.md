# 07 Weight Solving

Date started: 2026-06-01

## Scope

This audit section covers:

- `dynamite/weight_solvers.py`
- `LegacyWeightSolver`
- Python `NNLS`
- SciPy and CVXOPT solver paths
- mass/kinematic constraint matrix construction
- weight-file caching and chi-square metadata

## Evidence Reviewed

- `dynamite/weight_solvers.py`
- `dev_tests/test_nnls.py`
- `dev_tests/test_reimplement_nnls.py`
- orbit-library boundary findings in `06_orbit_library_boundary.md`

## Findings

### WS-001

Severity: High

Area: Legacy solver process failure detection

Files:

- `dynamite/weight_solvers.py`

Summary:

The legacy weight-solver wrapper treats empty stdout as success, even if the
subprocess return code is non-zero. This is the same failure-detection pattern
as OB-001 at the orbit-library boundary.

Evidence:

```text
weight_solvers.py:324-342
p = subprocess.run('bash '+cmdstr,
                   stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT,
                   shell=True)
...
if not p.stdout.decode("UTF-8"):
    self.logger.info(f'...done, NNLS problem solved - {cmdstr}'
                     f' exit code {p.returncode}. {log_file}')
```

Impact:

A failed legacy solver command can be logged as successful if it exits non-zero
without captured output. The code then proceeds to parse legacy output files and
may either fail late or convert stale files into a new weight file.

The GALAHAD runtime follow-up adds a stronger case: direct solver-mode `5`
runs for `triaxnnls_noCRcut` and `triaxnnls_CRcut` exited with shell status `0`
while their logs contained `QPB_solve exit status = -5` and still wrote output
files. So the wrapper must validate solver status in addition to subprocess
return code.

Recommendation:

Require `p.returncode == 0`, then validate solver-specific status from the log
or a machine-readable status file before reading outputs. Use stdout only as
diagnostic text. Prefer `subprocess.run(..., check=True)` with explicit
exception handling that records the command, return code, and log file.

Verification:

Generate a solver script that exits `1` with no output and assert that
`LegacyWeightSolver.solve()` raises before reading result files.

### WS-002

Severity: Medium

Area: Legacy solver script decompression checks

Files:

- `dynamite/weight_solvers.py`

Summary:

The generated legacy solver script uses `bunzip2 -c ... > ...` to decompress
orbit-library files without `set -e` or explicit file checks before running the
Fortran NNLS executable.

Evidence:

```text
weight_solvers.py:397-407
txt_file.write('#!/bin/bash' + '\n')
...
txt_file.write(f'test -e datfil/orblib_{self.ml}.dat || bunzip2 -c  datfil/orblib.dat.bz2 > datfil/orblib_{self.ml}.dat' + '\n')
...
txt_file.write(f'test -e {file_name} || '
               f'bunzip2 -c  datfil/orblib{f}.dat.bz2 > {file_name}\n')
```

The Fortran executable line has `|| exit 1`, but decompression lines do not:

```text
weight_solvers.py:418-421
... /triaxnnls_CRcut < {nn}.in >> {nn}ls.log || exit 1
```

Impact:

Missing or corrupt compressed orbit-library files can create empty or partial
temporary files and still allow the solver command to run. That can produce
misleading solver failures or stale/invalid outputs.

Recommendation:

Add `set -euo pipefail` to generated scripts, check decompression results, and
verify all decompressed inputs exist and are non-empty before invoking the
Fortran solver.

Verification:

Delete or corrupt one required `.bz2` file and assert the generated script fails
before running `triaxnnls_*`.

### WS-003

Severity: Medium

Area: CVXOPT solver status ignored

Files:

- `dynamite/weight_solvers.py`

Summary:

`CvxoptNonNegSolver` records whether CVXOPT reached an optimal solution, but
`NNLS.solve()` does not check that status before using `solver.beta`.

Evidence:

```text
weight_solvers.py:836-840
P = np.dot(A.T, A)
q = -1.*np.dot(A.T, b)
solver = CvxoptNonNegSolver(P, q)
weights = solver.beta
```

```text
weight_solvers.py:906-908
sol = cvxopt.solvers.qp(P, q, G, h)
self.success = sol['status']=='optimal'
self.beta = np.squeeze(np.array(sol['x']))
```

Impact:

Non-optimal CVXOPT results can be accepted as valid weights and saved with
chi-square metadata. This can silently contaminate model ranking.

Recommendation:

After constructing `CvxoptNonNegSolver`, require `solver.success` before using
`solver.beta`. If not optimal, return failed weights/chi-square or raise a clear
solver-status exception.

Verification:

Mock a CVXOPT result with `status != 'optimal'` and assert the model is marked
failed rather than saved as valid.

### WS-004

Severity: High

Area: Zero-error constraints in Python NNLS

Files:

- `dynamite/weight_solvers.py`

Summary:

Intrinsic-mass errors are floored to `1e-16`, but projected-mass errors and
kinematic errors after projected-mass scaling are not floored before dividing
the constraint vector and matrix by `econ`.

Evidence:

Intrinsic mass has a floor:

```text
weight_solvers.py:682-685
error = self.intrinsic_masses * self.intrinsic_mass_error
error = np.abs(np.ravel(error))
error[np.where(error<=0.)] = 1.0e-16
econ[idx] = np.abs(np.ravel(error))
```

Projected mass does not:

```text
weight_solvers.py:690-693
con[idx] = self.projected_masses
econ[idx] = np.abs(self.projected_masses * self.projected_mass_error)
orbmat[idx,:] = np.hstack(orblib.projected_masses).T
```

Kinematic errors are multiplied by projected mass:

```text
weight_solvers.py:705-708
obs_kins, obs_kins_err = tmp
obs_kins = (obs_kins.T * prj_mass_i).T
obs_kins_err = (obs_kins_err.T * prj_mass_i).T
```

Then all constraints are divided by `econ`:

```text
weight_solvers.py:727-728
rhs = con/econ
orbmat = (orbmat.T/econ).T
```

Impact:

Any zero projected mass or zero scaled kinematic error can produce `inf` or
`nan` entries in the NNLS matrix. Solver behavior then depends on backend
details and may fail late or return unusable weights.

Recommendation:

Validate `econ` before division. Reject non-finite or non-positive errors with
a clear message, or apply a documented floor consistently across all constraint
families.

Verification:

Add tests with a zero projected-mass aperture and assert construction fails
clearly before calling the solver.

### WS-005

Severity: Medium

Area: Solver-result finite validation

Files:

- `dynamite/weight_solvers.py`

Summary:

The Python NNLS path only checks `weights[0]` for `nan` before calculating
chi-square and saving output. It does not validate that all weights are finite
and non-negative.

Evidence:

```text
weight_solvers.py:851-856
if not np.isnan(weights[0]):
    # calculate chi2s
    chi2_vector = (np.dot(A, weights) - b)**2.
    chi2_tot = np.sum(chi2_vector)
```

Impact:

If a later weight is `nan` or `inf`, chi-square calculation can produce invalid
values and still write a weight file. If a backend returns tiny negative values,
the non-negativity contract is not checked before saving.

Recommendation:

Require:

```python
np.all(np.isfinite(weights)) and np.all(weights >= -tolerance)
```

Then clip only within a documented tolerance, or fail the model.

Verification:

Inject solver outputs with first weight finite and later `nan`/`inf`/negative
values and assert no valid weight file is written.

### WS-006

Severity: Medium

Area: Kinematic/orbit-library mismatch truncation

Files:

- `dynamite/weight_solvers.py`

Summary:

`construct_nnls_matrix_and_rhs()` zips configured kinematic datasets with orbit
LOSVD histograms. If their lengths differ, `zip()` silently truncates.

Evidence:

```text
weight_solvers.py:695-698
stars = self.system.get_unique_triaxial_visible_component()
kins_and_orb_losvds = zip(stars.kinematic_data, orblib.losvd_histograms)
...
for (kins, orb_losvd) in kins_and_orb_losvds:
```

Impact:

Missing orbit histograms for a configured kinematic dataset can silently remove
constraints from the NNLS problem. Extra orbit histograms can also be ignored.

Recommendation:

Check the counts before zipping:

```python
if len(stars.kinematic_data) != len(orblib.losvd_histograms):
    raise ValueError(...)
```

Verification:

Add a test with two configured kinematic datasets and one LOSVD histogram and
assert matrix construction fails explicitly.

### WS-007

Severity: Low

Area: `assert` used for solver selection

Files:

- `dynamite/weight_solvers.py`

Summary:

`NNLS.__init__()` validates `nnls_solver` with `assert`, which is disabled under
optimized Python.

Evidence:

```text
weight_solvers.py:609-612
if nnls_solver is None:
    nnls_solver = self.settings['nnls_solver']
assert nnls_solver in ['scipy', 'cvxopt'], 'Unknown nnls_solver'
self.nnls_solver = nnls_solver
```

Impact:

Invalid solver names are not rejected at construction under `python -O`; they
fail later in `solve()`.

Recommendation:

Replace the assertion with an explicit `if`/`raise ValueError`.

Verification:

Run the invalid-solver test with `PYTHONOPTIMIZE=1`.

### WS-008

Severity: Low

Area: Legacy weight-file reader drift

Files:

- `dynamite/weight_solvers.py`

Summary:

`LegacyWeightSolver.read_weights()` always defines an `lcut` column even though
the comment says that column is not present for some legacy solver variants.

Evidence:

```text
weight_solvers.py:444-455
col_names = [...]
             'lcut'] # lines 1321-1322 of triaxnnls_CRcut.f90
# NOTE: column 'lcut' is not present if different "triaxnnls" file used
dtype = [int, int, int, int, int, int, float, int]
weights = np.genfromtxt(fname,
                        skip_header=1,
                        names=col_names,
                        dtype=dtype)
```

Impact:

The helper may fail or misparse outputs from `triaxnnls_noCRcut` or barred
solver variants. It may be unused by the main path, but it is public code in the
solver layer.

Recommendation:

Detect the number of columns in `nn_orb.out` and choose column names/dtypes
accordingly.

Verification:

Add sample `nn_orb.out` fixtures for CRcut and noCRcut outputs.

## Positive Observations

- The Python NNLS path reconstructs the same conceptual constraint vector as
  the legacy path: total mass, intrinsic mass, projected mass, then kinematics.
- SciPy solver max iterations are configurable through `maxiter_factor`.
- Existing weight files are cached and can be reused, which is important for
  expensive model grids.
- Legacy/Python NNLS comparison tests exist in `dev_tests/test_reimplement_nnls.py`.

## Open Questions

- Should zero projected-mass apertures be impossible by construction, or should
  the solver explicitly support them?
- What solver-status policy should be used for CVXOPT non-optimal returns:
  fail hard, save failed row, or fallback to SciPy only if explicitly requested?
- Should the legacy and Python chi-square definitions be made identical, or is
  the documented difference intentional for backward compatibility?

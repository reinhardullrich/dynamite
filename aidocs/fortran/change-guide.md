# Fortran Backend Change Guide

Last updated: 2026-06-04

Purpose: practical checklist for changing, optimizing, or replacing the active
Fortran backend without breaking Python callers or scientific parity.

## First Checks

Before editing:

```bash
git status --short --branch
```

Confirm you are on the branch requested by the user. Current branch policy from
the user is to work on:

```text
Fortran-cleanup
```

Do not commit or push unless the user asks.

Never use code from `orblib_fortran/unused/`. That folder is
archive/reference-only. Do not restore, copy, adapt, compile, or test against
that code unless the user explicitly reverses this rule.

## Build And Test Commands

Build shared library:

```bash
make -C orblib_fortran shared
```

Fast Python API tests:

```bash
.venv/bin/python -m pytest tests/test_orblib_api.py
```

Fortran inventory and small kernel parity:

```bash
.venv/bin/python -m pytest tests/test_fortran_inventory.py tests/test_fortran_kernel_parity.py
```

Slow generated orbit-library output tests:

```bash
.venv/bin/python -m pytest tests/test_fortran_orblib_output.py
```

Use the slow tests when changing integration, projection, qgrid, LOSVD,
precision compatibility, output files, or cache behavior.

## ABI Change Checklist

If changing `source/orblib_c_api.f90` exported calls:

1. Update Fortran dummy arguments and implementation.
2. Update `ctypes` declarations in `dynamite/orblib_api.py`.
3. Update direct input builders:
   - `_orbitstart_memory_inputs(...)`
   - `_direct_orblib_inputs(...)`
4. Update `SHARED_LIBRARY_ABI_VERSION`.
5. Update `orblib_api_abi_version()`.
6. Add or adjust tests in `tests/test_orblib_api.py`.
7. Rebuild `liborblib_fortran.so`.
8. Run fast tests and relevant slow tests.
9. Update these `aidocs/fortran/` docs.

Never change the ABI silently while leaving version `2`.

## Inactive Legacy Routine Policy

Some Fortran routines are retained as commented blocks marked
`INACTIVE LEGACY ROUTINE`. These are old file-input, executable-driver, bar, or
helper paths that are not reachable from the active Python direct
shared-library ABI. Keep them commented unless the user explicitly asks to
restore a legacy executable/file-input path. If restoring one, update public
exports, makefile source expectations if needed, Python contract docs, and add
tests for that path before treating it as active again.

## Output Change Checklist

If changing qgrid, LOSVD, pops, orbit-class, compression, or done-marker
behavior:

1. Update the Fortran writer modules.
2. Update `dynamite/orblib.py` readers.
3. Update generated-output tests.
4. Regenerate fixtures only when the new output is scientifically accepted.
5. Document the new file contract in `output-contract.md`.

High-risk files:

- `orblib_fortran/source/orbit_library/*.f90`
- `dynamite/orblib.py`
- `tests/test_fortran_orblib_output.py`
- `tests/fixtures/orblib_losvd/`

## Precision Change Checklist

If touching direct input precision, begin-table values, or potential
interpolation:

1. Read `python-contract.md` precision section.
2. Preserve or deliberately replace the old text-interface compatibility:
   - Python `parameters_pot` quantization.
   - Fortran `9ES30.10` begin-row round-trip.
   - shared model-local `interpolgrid`.
3. Run slow generated LOSVD parity tests.
4. Compare aggregate mass, max difference, means, quantiles, and full-array
   fixture checks.
5. Treat small input perturbations as potentially large scientific output
   changes.

## Performance Change Checklist

Before optimizing:

1. Add or enable timing around the suspected hot section.
2. Measure one representative full model.
3. Estimate total-run payoff, not just local microbenchmark payoff.
4. Preserve deterministic output ordering.
5. Run parity tests after optimization.

Likely meaningful areas:

- DOP853 integration loop.
- potential interpolation / `interpolgrid` behavior.
- projection and symmetry loops.
- PSF/aperture/binning loops.
- LOSVD histogram accumulation.
- qgrid storage.
- Python process-level scheduling across model directories.

Likely low-payoff areas unless profiling proves otherwise:

- import-time cleanup
- one-time Python object construction
- single-use text formatting outside hot loops
- style-only Fortran refactors

## Parallelism Change Checklist

Current safe parallelism is across model directories or isolated Fortran worker
processes. One tube/box run is not currently chunked internally by Python.

If adding chunked parallelism for one model:

1. Define explicit orbit-bundle ranges.
2. Make every worker write to unique output roots.
3. Ensure each worker has safe cache behavior.
4. Define deterministic merge order.
5. Merge qgrid, LOSVD, pops, and orbit-class outputs.
6. Prove merged output equals single-run output.
7. Add tests that fail on missing chunks, duplicate chunks, and reordered
   orbit columns.

Do not run multiple writers into the same `datfil/<root>_*` files.

## Replacement Checklist

If replacing Fortran with Python/C++/Cython/Numba or another backend:

Minimum compatibility target:

- same orbit-start semantics
- same potential and dark-halo behavior
- same integration tolerances or scientifically accepted differences
- same projection symmetry behavior
- same PSF/aperture/binning semantics
- same LOSVD shape and units
- same qgrid intrinsic moment layout
- same orbit-class output or a documented replacement
- same Python `OrbitLibraryResult` behavior
- same or explicitly migrated fixture expectations

Recommended migration order:

1. Keep Python readers and output contract stable.
2. Replace one internal backend section behind tests.
3. Compare generated outputs against the current shared-library backend.
4. Only then simplify or remove old Fortran code.

## Documentation Update Rule

Update `aidocs/KNOWLEDGE.md` when current architecture, workflows, commands,
tests, or operational behavior change.

Update specific files under `aidocs/fortran/` when Fortran behavior or the
Python boundary changes.

Do not update `aidocs/CHANGES.md` automatically for every change. Use it only
when a human-readable historical note is useful.

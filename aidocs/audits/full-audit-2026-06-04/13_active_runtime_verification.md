# 13 Active Runtime Verification

Audit date: 2026-06-04

## Active Build Contract

Supported local build:

```bash
make -C orblib_fortran shared
```

Required artifact:

```text
orblib_fortran/build/lib/liborblib_fortran.so
```

## Active API Contract

The active non-bar orbit-library backend is `fortran_shared_library` in
`dynamite/orblib_api.py`.

Acceptance requirements:

- shared library exists;
- Python passes direct input arrays and output paths through `ctypes`;
- Fortran returns status `0`;
- Python raises on nonzero Fortran status;
- required `datfil/` outputs are compressed and readable;
- done markers are written only after generation/compression.

## Active Output Contract

Expected generated files per tube/box root:

- `<root>_qgrid.dat.bz2`
- `<root>_losvd_hist.dat.bz2`
- `<root>_pops.dat.bz2` when populations are generated/read
- `<root>.dat_orbclass.out`

Model-level done markers:

- `tube_done`
- `box_done`
- `tube_box_done`

Current gap:

- no versioned manifest with ABI version, input hashes, output sizes/hashes,
  warnings, and timings.

## Active Solver Contract

Current accepted config:

```yaml
weight_solver_settings:
  type: "NNLS"
  nnls_solver: "scipy"
```

Recommended future contract:

- explicit `SolverProblem`;
- explicit `SolverResult`;
- finite/non-negative weights;
- finite chi-square;
- backend status and diagnostics;
- matrix/rhs shape metadata and input hash.

## Current Test Coverage

Default pytest on 2026-06-04:

```text
62 passed, 6 skipped
```

Opt-in Fortran/output tests on 2026-06-04:

```text
11 passed
```

## Verification Gaps

- no real `Omega != 0` rotating-frame fixture;
- no full solver matrix-construction fixture;
- no atomic-write tests;
- no multi-kinematic-set/population direct-output fixture beyond current
  coverage;
- no performance timing manifest tests.

## Acceptance Rule For Future Fortran Changes

Before accepting changes to integration, projection, qgrid, PSF, aperture,
histogram, output, or direct ABI:

```bash
make -C orblib_fortran shared
.venv/bin/python -m pytest
DYNAMITE_RUN_SLOW_TESTS=1 DYNAMITE_RUN_ORBLIB_FORTRAN_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_orblib_output.py tests/test_fortran_inventory.py
```

For symmetry or rotating-frame changes, add and run an `Omega != 0` fixture
first.

# 13 Active Runtime Verification

Date: 2026-06-02

Scope: current active DYNAMITE runtime only. This chapter verifies the runtime
path that is used by this branch now:

1. Python configuration and model orchestration in `dynamite/`.
2. Direct shared-library orbit generation through `dynamite/orblib_api.py`.
3. `ctypes` calls into `orblib_fortran/build/lib/liborblib_fortran.so`.
4. Binary orbit-library outputs under model `datfil/` directories.
5. Readback through the current Python orbit-library readers.
6. Weight solving through Python `NNLS`.

## Active Build Contract

The supported Fortran runtime artifact is:

```text
orblib_fortran/build/lib/liborblib_fortran.so
```

The supported build commands are:

```bash
make -C orblib_fortran shared
make -C orblib_fortran all
make -C orblib_fortran nogal
```

For this branch, those targets are expected to build the same shared library.
The active package does not need standalone Fortran program binaries for normal
model generation.

Runtime checks should verify:

- the shared library exists at the configured path;
- the shared library exports `orblib_api_abi_version`;
- the exported ABI version is `2`;
- the shared library exports `orblib_api_run_orbitstart_memory`;
- the shared library exports `orblib_api_run_orblib_direct`.

## Active API Contract

Python owns input preparation. The active API passes typed arrays and scalars
directly to the shared library:

- MGE potential and luminous tables;
- orbit grid settings;
- dark-halo settings;
- orbit-start arrays;
- PSF tables;
- aperture geometry;
- spatial bin maps;
- velocity histogram settings;
- output paths.

The active orbit-generation API does not require generated Fortran input files
for orbit starts or orbit-library integration. Current output is still written
to binary files because the existing Python readers and weight solver consume
that format.

The active shared-library boundary should fail hard when:

- the shared library is missing;
- the ABI version is not the expected value;
- an exported function is missing;
- the worker process exits non-zero;
- the shared-library call returns a non-zero status;
- required output files are missing after generation;
- output arrays fail shape or finite-value validation.

## Active Output Contract

The current orbit-library output contract is binary `datfil/` content. The
active generation path writes and compresses the files that the existing Python
readers expect:

- `orblib_qgrid.dat.bz2`;
- `orblib_losvd_hist.dat.bz2`;
- `orblib.dat_orbclass.out`;
- `orblibbox_qgrid.dat.bz2`;
- `orblibbox_losvd_hist.dat.bz2`;
- `orblibbox.dat_orbclass.out`;
- `tube_done`;
- `box_done`;
- `orblib_done`.

This is not yet a memory-only output API. The current safe boundary is:

- Python supplies input in memory;
- Fortran writes the existing binary orbit-library files;
- Python reads those files through the established readers.

Moving output to memory should be treated as a separate refactor because it
changes the largest data contract in the runtime.

## Active Solver Contract

The active weight solver is Python `NNLS`.

Recommended current configuration:

```yaml
weight_solver_settings:
    type: "NNLS"
    nnls_solver: "scipy"
```

Runtime verification should check that:

- the orbit library can be read before solving;
- the NNLS matrix and right-hand side have the expected shapes;
- solver inputs are finite;
- returned weights are finite;
- returned weights are non-negative within the documented tolerance;
- chi-square values are finite;
- model status is written only after validated output exists.

Chapter 15 expands this into the proposed `SolverProblem` and `SolverResult`
policy.

## Current Test Coverage

The current pytest baseline covers the active runtime through focused tests:

- `tests/test_orblib_api.py` checks the Python API facade, request/result
  objects, shared-library path handling, direct input extraction, and orbit-start
  memory call behavior.
- `tests/test_fortran_inventory.py` checks the active Fortran source inventory
  and verifies the shared-library artifact when opt-in Fortran tests are
  enabled.
- `tests/test_fortran_orblib_output.py` regenerates the small NGC6278
  orbit-library fixture when opt-in slow Fortran tests are enabled and compares
  the generated LOSVD output against the current shared-library fixture.
- `tests/test_reference_fixtures.py` checks small extracted fixture contracts.
- `tests/test_example_catalog.py` checks active example configuration defaults,
  including Python `NNLS`.

Fast baseline:

```bash
.venv/bin/python -m pytest tests -m "not slow and not orblib_fortran"
```

Opt-in shared-library checks:

```bash
make -C orblib_fortran shared
DYNAMITE_RUN_ORBLIB_FORTRAN_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_inventory.py tests/test_orblib_api.py -m orblib_fortran
```

Opt-in slow output check:

```bash
make -C orblib_fortran shared
DYNAMITE_RUN_SLOW_TESTS=1 DYNAMITE_RUN_ORBLIB_FORTRAN_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_orblib_output.py
```

## Verification Gaps

The following active-runtime checks are still missing or incomplete:

- no per-stage timing manifest for orbit-start, tube integration, box
  integration, compression, readback, matrix assembly, solve, and writeback;
- no explicit binary output schema version stored with each orbit-library file
  set;
- no memory-only output API for the large orbit-library arrays;
- no first-class `SolverProblem` object for deterministic solver fixtures;
- no first-class `SolverResult` object for backend status, diagnostics, and
  validation;
- no strict cache key for prepared solver matrices.

These are improvement targets for the active runtime contract.

## Acceptance Criteria

The active runtime should be considered verified when a fresh checkout can:

1. build `orblib_fortran/build/lib/liborblib_fortran.so`;
2. load the shared library from Python and confirm ABI version `2`;
3. generate orbit starts through the memory-input API;
4. generate tube and box orbit libraries through direct Python inputs;
5. write the expected binary `datfil/` outputs;
6. read LOSVD histograms, intrinsic masses, projected masses, and orbit
   classifications back through Python;
7. solve weights through Python `NNLS`;
8. validate finite/non-negative solver output;
9. pass the fast pytest baseline;
10. pass opt-in shared-library and slow LOSVD checks when the shared library is
    built and the relevant environment flags are set.

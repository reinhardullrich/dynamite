# Fortran Source Map

Last updated: 2026-06-04

Purpose: map active Fortran source files and the responsibilities of the large
orbit-library engine modules.

## Active Build Output

Supported runtime artifact:

```text
orblib_fortran/build/lib/liborblib_fortran.so
```

Supported build command:

```bash
make -C orblib_fortran shared
```

Active build control files:

```text
orblib_fortran/makefile
orblib_fortran/makefile.linux
```

GNU Make finds lowercase `makefile` automatically for the normal build. Use
`make -C orblib_fortran -f makefile.linux shared` only when explicitly testing
the Linux-specific variant.

The active build is shared-library oriented. Old executable drivers and other
inactive retained files remain under `orblib_fortran/unused/` for reference but
are not the supported runtime path.

Hard rule: never use code from `orblib_fortran/unused/` for active
builds, new runtime paths, tests, or refactors. That directory is
archive/reference-only. If a future task seems to need something from
`orblib_fortran/unused/`, stop and ask the user before restoring or copying it.

## Active Source Layout

```text
orblib_fortran/source/orblib_c_api.f90
orblib_fortran/source/initial_parameters.f90
orblib_fortran/source/potential/triaxial_stellar_potential.f90
orblib_fortran/source/potential/dark_halo_potential.f90
orblib_fortran/source/potential/interpolated_potential.f90
orblib_fortran/source/orbit_start_library.f90
orblib_fortran/source/orbit_library/random_gauss_generator.f90
orblib_fortran/source/orbit_library/orbit_integrator.f90
orblib_fortran/source/orbit_library/projection.f90
orblib_fortran/source/orbit_library/psf.f90
orblib_fortran/source/orbit_library/aperture_base.f90
orblib_fortran/source/orbit_library/aperture_boxed.f90
orblib_fortran/source/orbit_library/aperture_dispatch.f90
orblib_fortran/source/orbit_library/spatial_binning.f90
orblib_fortran/source/orbit_library/losvd_histograms.f90
orblib_fortran/source/orbit_library/intrinsic_qgrid.f90
orblib_fortran/source/orbit_library/orbit_output.f90
orblib_fortran/source/orbit_library/orbit_library_runner.f90
orblib_fortran/source/numerics/dop853.f
orblib_fortran/source/numerics/dqxgs.f
orblib_fortran/source/numerics/ellipint.f90
orblib_fortran/source/numerics/numeric_kinds_f.f90
orblib_fortran/source/numerics/numrec_arloc.f
orblib_fortran/source/numerics/ran1_nr.f90
orblib_fortran/source/numerics/specfunc_beta.f90
```

## File Responsibilities

The orbit-library engine used to live in one large file,
`orblib_f_new_mirror.f90`. It has been split one module per file for human
readability. Fortran module names were intentionally not changed in that split.

Several old file-input, executable-driver, and bar setup routines are retained
as commented code blocks marked `INACTIVE LEGACY ROUTINE`. They are not needed
by the active Python direct shared-library path because Python now passes model
parameters, orbit starts, PSF tables, apertures, histograms, bin maps, and
output paths through `orblib_c_api.f90` instead of letting Fortran prompt for
or read legacy `infil/` files. They are commented instead of deleted so the old
workflow remains available as historical reference while the active build only
exposes direct-array entry points.

## File Responsibilities

### `orblib_c_api.f90`

C ABI boundary for Python `ctypes`.

Exports:

- `orblib_api_abi_version`
- `orblib_api_run_orbitstart_memory`
- `orblib_api_run_orblib_direct`

Responsibilities:

- accept Python-owned arrays and scalars
- load model parameters into Fortran modules through `iniparam_from_arrays`
- call orbit-start generation for in-memory begin tables
- call `high_level.setup_direct`, `run`, and `stob` for tube/box libraries
- return integer status codes to Python

Do not add hidden filesystem inputs here. The point of this file is to keep the
active Python path direct and explicit.

### `orbit_library/*.f90`

Main orbit-library engine, split by existing Fortran module. These files
integrate orbits, project them, apply PSF/aperture/binning logic, accumulate
histograms and intrinsic grids, and write binary outputs.

Files and retained module names:

- `orbit_library/random_gauss_generator.f90`: module `random_gauss_generator`;
  Gaussian random offsets for PSF sampling.
- `orbit_library/orbit_integrator.f90`: module `integrator`; orbit-start table
  setup, DOP853 integration, dense output
  sampling, orbit classification, and direct begin-table compatibility
  rounding.
- `orbit_library/projection.f90`: module `projection`; viewing-angle
  projection and symmetry projections.
- `orbit_library/psf.f90`: module `psf`; point-spread-function setup and
  Gaussian displacement sampling.
- `orbit_library/aperture_base.f90`: module `aperture`; common aperture
  interface.
- `orbit_library/aperture_boxed.f90`: module `aperture_boxed`;
  rectangular/pixel aperture lookup.
- `orbit_library/aperture_dispatch.f90`: module `aperture_routines`; dispatch
  layer for aperture implementations.
- `orbit_library/spatial_binning.f90`: module `binning`; maps aperture pixels
  to spatial bins.
- `orbit_library/losvd_histograms.f90`: module `histograms`; LOSVD velocity-bin
  accumulation.
- `orbit_library/intrinsic_qgrid.f90`: module `quadrantgrid`; intrinsic 3D
  qgrid setup, storage, and writing.
- `orbit_library/orbit_output.f90`: module `output`; output file setup,
  append/write routines, and close routines.
- `orbit_library/orbit_library_runner.f90`: module `high_level`; orchestrates
  setup, run loop, and shutdown.

Active direct entry inside this file:

```text
high_level.setup_direct(...)
high_level.run()
high_level.stob()
```

### `orbit_start_library.f90`

Orbit-start generation for tube and box orbit libraries. The active Python path
calls it through `orblib_api_run_orbitstart_memory`, not by writing and reading
legacy `begin.dat` files.

Outputs are returned to Python as begin arrays and `noreg` flags.

### `initial_parameters.f90`

Global parameter setup layer for potential, orbit grid, dark halo, and related
model inputs. The direct ABI calls `iniparam_from_arrays(...)` instead of
requiring legacy text input files.

### `potential/triaxial_stellar_potential.f90`

Triaxial stellar potential calculation based on the MGE model and intrinsic
geometry.

### `potential/dark_halo_potential.f90`

Dark-matter potential support.

### `potential/interpolated_potential.f90`

Potential interpolation. This file reads and writes the bare `interpolgrid`
cache in the current working directory.

Important:

- The cache path is not passed as an explicit parameter.
- Python controls cache isolation by setting the worker current working
  directory to the model directory.
- Cache format changes require parity tests because orbit integration is
  sensitive to interpolation details.

### `numerics/ran1_nr.f90`

Free-form Fortran 90 version of the legacy `ran1` random-number generator used
by Fortran routines. It remains an external function named `ran1` so existing
call sites do not need module changes.

### `source/numerics/*`

Bundled numerical kernels:

- `dop853.f`: DOP853 ODE integrator used for orbit integration.
- `dqxgs.f`: numerical quadrature support.
- `ellipint.f90`: elliptic integrals.
- `numeric_kinds_f.f90`: numeric kind definitions.
- `numrec_arloc.f`: Numerical Recipes allocation/support routines.
- `specfunc_beta.f90`: beta/special-function support.

Treat these as vendored numerical routines. Avoid style-only edits.

## Retained Inactive Sources

```text
orblib_fortran/unused/orblibprogram.f90
orblib_fortran/unused/orblibprogram_bar.f90
orblib_fortran/unused/orbitstart.f90
orblib_fortran/unused/orbitstart_bar.f90
orblib_fortran/unused/dopri5.f
orblib_fortran/unused/pij.f90
orblib_fortran/unused/cutest_makefile
orblib_fortran/unused/Changelog.txt
```

These are not active runtime sources. They are retained for reference and
historical comparison.

Never use them in active builds, tests, refactors, or replacement work unless
the user explicitly reverses this rule. Do not restore, copy, or adapt them
silently.

## Archived Solver Sources

Legacy Fortran NNLS/GALAHAD material was moved out of the active build and is
archived under:

```text
archive/legacy_nnls_fortran/
```

The active runtime rejects `LegacyWeightSolver`. Use Python `NNLS`.

## Practical File-Edit Guidance

- For Python-callable ABI changes, edit `source/orblib_c_api.f90` and
  `dynamite/orblib_api.py` together.
- For runtime behavior changes, expect most edits in `source/orbit_library/`.
- For orbit-start changes, inspect `source/orbit_start_library.f90`,
  `source/initial_parameters.f90`, and the Python begin-table handling together.
- For potential/cache changes, inspect `source/potential/` and the Python
  `interpolgrid` working-directory logic.
- For output changes, inspect the `output`, `quadrantgrid`, and `histograms`
  modules plus Python readers in `dynamite/orblib.py`.

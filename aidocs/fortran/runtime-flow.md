# Fortran Runtime Flow

Last updated: 2026-06-04

Purpose: describe what the active Fortran backend does during one orbit-library
generation run.

## High-Level Sequence

For one model, Python generates a complete orbit library in this order:

```text
1. Create model/datfil directory.
2. Run orbit-start generation.
3. Run tube orbit-library part.
4. Run box orbit-library part.
5. Compress binary outputs.
6. Calculate Python intrinsic MGE masses.
7. Touch completion markers.
8. Read generated files through Python readers when needed.
```

The Fortran part is steps 2-4. Python owns directory setup, compression,
completion markers, readers, intrinsic mass side files, and weight solving.

## Orbit-Start Generation

Python calls:

```text
SharedLibraryFortranOrbitBackend.run_orbitstart_memory()
```

Fortran receives direct arrays through:

```text
orblib_api_run_orbitstart_memory
```

Fortran then:

```text
iniparam_from_arrays(...)
ip_setup(...)
runorbitstart_memory(...)
ip_stop()
```

The output stays in memory and returns to Python:

- tube begin rows
- box begin rows
- tube `noreg` flags
- box `noreg` flags
- row counts
- status code

No active Python path requires legacy `begin.dat` or `beginbox.dat` files.

## Tube And Box Orbit-Library Runs

Python calls the direct orbit-library ABI twice:

```text
orblib_api_run_orblib_direct(..., file root "orblib", ...)
orblib_api_run_orblib_direct(..., file root "orblibbox", ...)
```

Tube and box calls use the same Fortran execution pipeline. They differ by
their begin tables, `noreg` flags, and output file root.

Fortran internal sequence:

```text
iniparam_from_arrays(...)
high_level.setup_direct(...)
high_level.run()
high_level.stob()
ip_stop()
```

## `high_level.setup_direct`

Direct setup wires Python-owned arrays into the old module-oriented Fortran
engine:

```text
integrator_setup_direct(...)
projection_setup()
qgrid_setup()
psf_setup_direct(...)
aperture_setup_direct(...)
histogram_setup_direct(...)
output_setup_direct(...)
```

Important setup responsibilities:

- assign begin rows to integrator state
- preserve legacy begin-row precision using `9ES30.10`
- configure projection angles and symmetry count
- allocate qgrid storage
- configure PSF Gaussian tables
- configure aperture maps
- configure LOSVD histogram binning
- open output files

## Main Run Loop

The core loop is in `high_level.run()`.

Conceptually:

```text
for each output orbit bundle:
  reset qgrid and histogram accumulators

  for each dithered starting point in the bundle:
    integrate orbit trajectory
    classify orbit family
    store intrinsic qgrid samples
    project trajectory through allowed symmetries
    apply PSF sampling
    map projected points into apertures/spatial bins
    bin line-of-sight velocities into LOSVD histograms

  write one orbit bundle's qgrid, LOSVD, optional pops, and class output
```

The code stores one output orbit bundle for a group of `dithering^3`
integrated starting trajectories. Be explicit about the word "orbit" when
working here:

- integrated physical trajectory
- dithered trajectory
- output orbit bundle
- tube/box orbit-library column
- final weight-solver column

These are related but not always identical counts.

## Integration

Orbit integration happens through:

```text
integrator_integrate(...)
  -> real_integrator / DOP853
  -> derivs(...)
  -> interpolpot.ip_accel(...)
  -> triaxpotent + dmpotent potential terms
  -> SOLOUT dense-output sampling
```

The expensive numerical core is orbit integration plus the per-sample
projection/PSF/aperture/histogram/qgrid work. There is no active OpenMP-style
parallel region inside the current Fortran engine.

## Projection And Symmetry

The projection module transforms intrinsic positions/velocities into projected
coordinates and line-of-sight velocities.

For a normal triaxial run, the code considers symmetry projections. This is
scientifically sensitive because sign conventions and orbit-family behavior
control how mass is mirrored into observed apertures.

Do not simplify projection loops by intuition alone. Changes require parity
tests against existing binary outputs and domain review.

## PSF, Aperture, Binning, LOSVD

After projection:

```text
psf_gaussian(...)
aperture_boxed_find(...)
histogram_store(...)
```

Responsibilities:

- PSF: displace projected points according to configured Gaussian PSF
  components.
- Aperture: find which aperture pixel receives the projected point.
- Binning: map aperture pixels to spatial bins.
- Histogram: accumulate line-of-sight velocity distribution counts in velocity
  bins.

This path is potentially performance-relevant because it runs for many sampled
trajectory points.

## Intrinsic QGrid

The qgrid path accumulates intrinsic 3D orbit information:

```text
qgrid_setup()
qgrid_reset()
qgrid_store(...)
qgrid_write()
```

The qgrid output is consumed by Python as intrinsic orbit moments and orbit
mass/shape information. Its layout is part of the binary output contract.

`qgrid_store()` contains old symmetry/projection logic. It is a candidate for
careful optimization, but only with profiling evidence and parity tests.

## Output

The output module handles raw Fortran files:

```text
output_setup_direct(...)
output_write()
stob()
```

For every tube/box output root, Fortran writes:

```text
datfil/<root>_qgrid.dat
datfil/<root>_losvd_hist.dat
datfil/<root>_pops.dat
datfil/<root>.dat_orbclass.out
datfil/<root>_qgrid.dat.tmp
```

Python later compresses selected raw binary files to `.bz2`.

## Parallelism Boundary

The Fortran engine itself is effectively single-process and single-threaded for
one tube or box call.

DYNAMITE parallelism exists above this layer:

- running multiple models at once
- isolating each Fortran call in its own worker process
- generating different model directories independently

Python cannot currently split one tube or box orbit-library call into multiple
independent chunks without changing Fortran output semantics and merge logic.
To do that safely, the backend would need explicit chunk ranges, independent
output roots, deterministic merge code, and cache/output race handling.

## What Python Does After Fortran

After successful Fortran calls, Python:

- compresses raw binary outputs
- writes `tube_done`, `box_done`, and `tube_box_done`
- computes or writes intrinsic MGE mass side files
- reads orbit-library outputs through `LegacyOrbitLibrary`
- transforms LOSVD histograms to observable kinematic matrices
- solves weights through Python `NNLS`

The active Fortran backend does not perform the final NNLS solve.


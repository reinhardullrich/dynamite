# Fortran Performance And Output-Size Review

Last updated: 2026-06-04

Purpose: review the active Fortran orbit-library backend for speed and output
file size. This is a static code-review note, not a measured profiler report.
Treat payoff estimates as hypotheses until confirmed on a representative model.

## Executive Summary

The build already uses aggressive local CPU optimization flags:
`-O3 -march=native -ffast-math -fomit-frame-pointer -funroll-loops`
in `orblib_fortran/makefile`. The next meaningful speedups are therefore not
"turn on optimization", but reducing repeated work in hot loops and changing
output/storage layout.

Highest-value candidates:

1. Avoid computing rotating-frame-only velocity-dispersion moments in normal
   non-rotating runs.
2. Replace `qgrid_store()`'s eight-way symmetry search with direct octant/sign
   selection.
3. Precompute PSF-to-aperture dispatch lists and other per-setup lookup tables
   instead of scanning them inside the per-orbit loop.
4. Split or version qgrid output so normal weight solving can read/store only
   density, while full intrinsic moments remain optional.
5. Consider sparse qgrid records. LOSVD output is already a compact
   contiguous-nonzero-range format; qgrid is the less optimized file.

## Current Runtime Shape

The hot active loop is `high_level.run()`:

- integrate each dithered trajectory;
- classify the trajectory;
- store intrinsic qgrid samples;
- project through eight triaxial projections;
- apply PSF sampling;
- map to aperture bins;
- accumulate LOSVD histograms;
- write one orbit bundle.

Evidence:

- `orblib_fortran/source/orbit_library/orbit_library_runner.f90:157-190`
  contains the orbit/dither/projection/PSF/aperture/histogram loop.
- `orblib_fortran/source/orbit_library/orbit_integrator.f90:418-566`
  calls DOP853 and retries on energy-conservation failure.
- `orblib_fortran/source/orbit_library/orbit_output.f90:258-311`
  writes one orbit bundle.

There is no active OpenMP region inside the Fortran backend. DYNAMITE parallel
execution happens above this layer by running model/backend workers in separate
processes.

## Performance Findings

### PF-01: Skip Rotating-Frame-Only Moment Work In Non-Rotating Runs

Finding: `integrator_find_orbtype()` computes cylindrical velocity-dispersion
moments `moments2` for every integrated trajectory, but active non-bar
triaxial runs only write those values inside the `Omega /= 0.0_dp` branch.

Evidence:

- `orbit_integrator.f90:315` always calls
  `integrator_find_orbtype(otype, moments, moments2, pos, vel)`.
- `orbit_integrator.f90:320-340` uses `moments2` only when
  `Omega /= 0.0_dp`.
- `orbit_integrator.f90:775-792` computes `vr`, `vt`, `vz`, means, and
  standard deviations over all sampled points.
- Python orbit-property reading expects five standard columns from
  `orbclass.out`, not these rotating-frame extras:
  `dynamite/orblib.py:1120-1151`.

Improvement: split `integrator_find_orbtype()` into always-needed orbit type
and five `moments` columns, plus optional rotating-frame diagnostics. In normal
`Omega == 0` runs, do not compute `moments2`.

Potential payoff: medium. It removes several full-array passes over
`integrator_points` per dithered trajectory. With `sampling: 50000`, this is
not tiny.

Risk: low/medium. The main risk is accidentally changing `orbclass.out` or
orbit classification. Tests must compare generated LOSVD/qgrid outputs and
`orbclass.out` structure before and after.

### PF-02: Replace QGrid Eight-Way Positive-Octant Search

Finding: `qgrid_store()` loops over all eight symmetry projections for every
sampled point, but the comment says the test passes only once per point.

Evidence:

- `intrinsic_qgrid.f90:182-218` loops `i = 1, size(proj, 1)` and then
  `j = 1, 8`.
- `intrinsic_qgrid.f90:185-186` says it finds the one projection in the
  positive octant and that doing this with a loop is stupid.
- Only the branch at `intrinsic_qgrid.f90:194-217` stores anything.

Improvement: compute the needed sign projection directly from the signs of
`x`, `y`, and `z`, then apply the matching velocity sign row. For rotating
models, preserve the four-fold/eight-slot convention currently selected by
`Omega`.

Potential payoff: medium to high inside qgrid work. It removes up to seven
failed branch tests and sign multiplications per sampled point. Total-run
payoff depends on how much time is qgrid versus DOP853 integration.

Risk: medium. Symmetry conventions affect scientific output. Implement only
with a table-driven mapping and parity tests against existing generated qgrid
and LOSVD fixtures.

### PF-03: Precompute Sign Tables Once Per Setup

Finding: both `qgrid_store()` and `project_n()` declare full sign tables,
assign `vsgn=vsgn1`, `psgn=psgn1`, and branch on `Omega` inside routines that
are called repeatedly.

Evidence:

- `intrinsic_qgrid.f90:104-164` builds/selects qgrid sign tables inside
  `qgrid_store()`.
- `projection.f90:100-158` builds/selects projection sign tables inside
  `project_n()`.
- `projection.f90:36-47` has a setup routine where these choices could be
  established once.

Improvement: move selected sign tables to module state during setup, or expose
a shared sign-table module. `project_n()` and `qgrid_store()` should only index
already-selected arrays.

Potential payoff: low to medium. The table copies are small, but the calls are
frequent. This is mostly cleanup that removes avoidable work and reduces the
chance of inconsistent sign-table edits.

Risk: low/medium. Parity tests still required because sign tables are
scientifically sensitive.

### PF-04: Precompute PSF To Aperture Dispatch

Finding: for every projection, the run loop iterates over every PSF and then
every aperture, checking `if (i == aperture_psf(ap))`.

Evidence:

- `orbit_library_runner.f90:177-185` performs the nested `psf_n` by
  `aperture_n` scan.
- `aperture_boxed_find()` and `histogram_store()` are only called for matching
  apertures.

Improvement: during aperture setup, create a compact list of aperture indices
for each PSF. The runtime loop becomes:

```text
for each psf:
  psf_gaussian(...)
  for ap in apertures_for_this_psf:
    aperture_boxed_find(...)
    histogram_store(...)
```

Potential payoff: low to medium for small models; medium for many apertures or
many kinematic/population datasets. It removes branchy dispatch work and makes
the hot loop easier to optimize.

Risk: low. This should be behavior-preserving if the aperture order remains
identical.

### PF-05: Avoid Reopening Output Files For Every Orbit Bundle

Finding: `output_write()` opens, appends, closes, and updates the status file
for every orbit bundle.

Evidence:

- `orbit_output.f90:266-309` opens/writes/closes the status, qgrid, optional
  pops, and LOSVD files per orbit bundle.

Improvement: keep qgrid/LOSVD/pops handles open during the active run and flush
periodically, while preserving the existing resume/status semantics. A safer
intermediate step is to keep the data files open but continue updating the
status file per orbit.

Potential payoff: low on local SSD when integration dominates; medium on slow
or network filesystems and for small/fast orbit libraries.

Risk: medium. The current reopen-per-orbit behavior supports crude resume and
reduces loss after interruption. Any change must define crash/resume semantics.

### PF-06: Reuse Binning Workspace

Finding: `binning_add_it_up()` creates a temporary array sized by
`bin_max(ap)` and velocity bins each time an orbit histogram is written for an
aperture.

Evidence:

- `spatial_binning.f90:168-184` allocates automatic local `t` and copies it
  back into `h`.
- It is called from `histogram_write()` at
  `losvd_histograms.f90:96-107`.

Improvement: allocate one reusable module-level workspace at setup with maximum
needed dimensions, or accumulate directly into output bins when the binning map
is known.

Potential payoff: low to medium. It affects output-time work, not the inner
per-sample loop. It may matter when spatial binning maps are large.

Risk: low/medium. Must preserve exact binned histogram ordering.

### PF-07: Reduce Temporary Decompression Files In Python Readers

Finding: Python decompresses `.bz2` outputs to temporary `.dat` files before
reading them with `scipy.io.FortranFile`.

Evidence:

- `dynamite/orblib.py:710-714` decompresses qgrid to a temp file.
- `dynamite/orblib.py:767-774` decompresses LOSVD to a temp file.
- `dynamite/orblib.py:871-875` decompresses pops to a temp file.

Improvement: test whether `FortranFile` can read a suitable file-like object
backed by decompressed bytes or a streaming wrapper. If not, keep the current
path for correctness. This is more about disk churn and read latency than final
stored size.

Potential payoff: low to medium, depending on output size and filesystem.

Risk: medium. `FortranFile` expects Fortran record markers and may require
seekable behavior. Do not replace without tests on large files.

## Output-Size Findings

### OF-01: QGrid Stores 16 Dense Channels Per Orbit Bundle

Finding: qgrid writes a dense 4D array for every orbit bundle:
`16 * quad_nph * quad_nth * quad_nr` double values, even when most consumers
only need density channel 0.

Evidence:

- `qgrid_setup()` allocates `quadrant_light(16, quad_nph, quad_nth, quad_nr)`
  at `intrinsic_qgrid.f90:52`.
- `qgrid_write()` writes the whole dense array at
  `intrinsic_qgrid.f90:273-274`.
- Python always reads the full array with `fort_file.read_reals(float)` and
  reshapes it at `dynamite/orblib.py:625-638`.
- Normal `read_orbit_base(..., return_intrinsic_moments=False)` only returns
  `density_3D_orb = quad_light[:,:,:,0]`.

Raw size estimate:

```text
bytes_per_orbit_bundle = 16 * quad_nr * quad_nth * quad_nph * 8
```

With the common default `quad_nr=10`, `quad_nth=6`, `quad_nph=6`, that is
`16 * 10 * 6 * 6 * 8 = 46,080` raw bytes per output orbit bundle, before
Fortran record overhead and compression. A density-only qgrid record would be
about 16x smaller for the qgrid payload.

Improvement options:

- Versioned density-only qgrid file for normal weight solving.
- Keep full intrinsic moments in a separate optional file written only when
  requested.
- Store sparse nonzero qgrid cells per orbit bundle.
- Store selected channels only: density plus a small documented subset.

Potential payoff: high for qgrid disk size and qgrid read time, especially for
large orbit grids or workflows that never call intrinsic-moment analysis.

Risk: medium/high. This changes the binary output contract and Python readers.
It needs format versioning and fixtures.

### OF-02: QGrid Sparse Encoding May Be Better Than Dense Encoding

Finding: qgrid is written dense even though each orbit bundle may touch only a
subset of 3D bins. The code normalizes and writes the whole array for every
bundle.

Evidence:

- Per-sample storage increments only one grid cell at a time:
  `intrinsic_qgrid.f90:209-216`.
- Whole-array normalization and write happen at
  `intrinsic_qgrid.f90:245-274`.

Improvement: after normalization, collect cells where channel 0 density is
nonzero and write `(ir, ith, iph, selected_channels...)`. This is independent
of the in-memory representation.

Potential payoff: model-dependent. If qgrid occupancy is low, this can be much
smaller than dense qgrid. If almost all cells are touched, dense plus
compression may be better.

Risk: medium/high because readers and fixtures must change. Add a measurement
first: for representative models, record nonzero qgrid cells per orbit bundle.

### OF-03: LOSVD Histogram Output Is Already Partly Sparse

Finding: LOSVD output does not write full velocity histograms for every
aperture. It stores a begin/end velocity-bin range and then only the contiguous
range with nonzero values.

Evidence:

- `histogram_write_compat_sparse()` scans each aperture histogram to find first
  and last positive velocity bin at `losvd_histograms.f90:118-126`.
- It writes `bout, eout` and only `t(ap, b:e)` at
  `losvd_histograms.f90:128-133`.
- Python reconstructs dense arrays at `dynamite/orblib.py:825-833`.

Conclusion: LOSVD file size is not obviously wasteful. A fully sparse
index/value format could beat the current contiguous-range format only if
velocity histograms have many internal zero gaps. Physical LOSVDs are usually
contiguous enough that the current format is plausible.

Improvement: before changing LOSVD format, measure average `(e-b+1)/hist_bins`
and internal zero fraction for representative outputs.

Potential payoff: low to medium.

Risk: medium. The Python reader and all LOSVD fixtures depend on the current
record ordering.

### OF-04: Bzip2 Optimizes Stored Size But Costs Time

Finding: Python compresses qgrid, pops, and LOSVD raw files to `.bz2` and then
deletes the raw files.

Evidence:

- `dynamite/orblib_api.py:270-301` compresses raw Fortran outputs with
  `bz2.open(...)`, replaces the staging file, and deletes the raw file.

Conclusion: final stored size is already compressed. Changing compression
could improve runtime, but not necessarily size. Bzip2 is often slow and fairly
compact. Zstandard or lower compression levels may improve wall time at the
cost of some disk size; xz may reduce size at the cost of time. This needs a
benchmark on real `datfil/` outputs.

Improvement: benchmark `bz2` levels, `gzip`, `xz`, and optionally `zstd`
against representative qgrid and LOSVD files. Do not change the extension or
reader contract until the benchmark proves the tradeoff.

Potential payoff: medium for read/write wall time; uncertain for final size.

Risk: low/medium if kept behind a versioned output policy; medium if changing
default file extensions.

### OF-05: Intrinsic Moment Cache Can Duplicate Large Data

Finding: when intrinsic moments are requested, Python reads both qgrid files,
builds a full `intmoms` array, and can write `datfil/intmoms.npz`.

Evidence:

- `read_orbit_intrinsic_moments()` reads qgrid with
  `return_intrinsic_moments=True` at `dynamite/orblib.py:1083-1090`.
- It saves compressed cache `intmoms.npz` at `dynamite/orblib.py:1108-1113`.

Conclusion: this is useful caching, but it can duplicate large qgrid-derived
data on disk. For default workflows that only need weights, avoid creating this
cache. For analysis workflows, the cache may be a net win.

Improvement: document or expose a clear "do not cache intrinsic moments" path
for large runs, and make sure automation does not request intrinsic moments
unnecessarily.

Potential payoff: high for disk footprint in analysis-heavy runs; no effect on
the raw Fortran output files.

Risk: low.

## Recommended Implementation Order

1. Add measurement before refactor:
   - total time in integration, qgrid, projection, PSF, aperture, histogram,
     output, and compression;
   - qgrid nonzero-cell fraction per orbit;
   - LOSVD contiguous-range fraction and internal zero fraction;
   - raw and compressed file sizes by suffix.
2. Implement PF-01 because it is narrow and likely behavior-preserving for
   `Omega == 0` runs.
3. Implement PF-04 because it is simple and makes the hot loop clearer.
4. Prototype PF-02 with a table-driven direct octant mapping and compare
   binary outputs.
5. Only after measurements, design a versioned qgrid output change:
   density-only, sparse, or optional full moments.

## Required Tests For Any Change

Run at minimum:

```bash
make -C orblib_fortran shared
.venv/bin/python -m pytest tests/test_orblib_api.py
.venv/bin/python -m pytest tests/test_fortran_inventory.py tests/test_fortran_kernel_parity.py
DYNAMITE_RUN_SLOW_TESTS=1 DYNAMITE_RUN_ORBLIB_FORTRAN_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_orblib_output.py
```

For output-format changes, add a new explicit format-version test and keep
legacy-reader coverage until old outputs are intentionally unsupported.


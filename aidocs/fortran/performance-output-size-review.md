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

Status: implemented on 2026-06-04.

Original finding: `integrator_find_orbtype()` computed cylindrical
velocity-dispersion moments `moments2` for every integrated trajectory, but
active non-bar triaxial runs only write those values inside the
`Omega /= 0.0_dp` branch.

Evidence:

- `orbit_integrator.f90` now calls
  `integrator_find_orbtype(otype, moments, pos, vel)` for standard orbit
  classification and five standard orbit-property moments.
- `orbit_integrator.f90` now calls
  `integrator_find_rotating_moments(moments2, pos, vel)` only inside the
  existing `Omega /= 0.0_dp` branch.
- The rotating helper contains the old `vr`, `vt`, `vz`, mean, and standard
  deviation calculations unchanged.
- Python orbit-property reading expects five standard columns from
  `orbclass.out`, not these rotating-frame extras:
  `dynamite/orblib.py:1120-1151`.

Implementation: split the always-needed orbit type and five `moments` columns
from the rotating-frame diagnostics. In normal `Omega == 0` runs, the backend
does not compute `moments2`. In rotating runs, the same `moments2` formulas are
still called before writing the rotating-frame diagnostic line.

Potential payoff: medium. It removes several full-array passes over
`integrator_points` per dithered trajectory. With `sampling: 50000`, this is
not tiny.

Risk after implementation: low for normal non-rotating runs if generated
LOSVD/qgrid parity tests pass, because the standard orbit-classification and
five standard moment formulas are unchanged. Rotating-frame behavior still
needs a dedicated test before treating this path as scientifically verified.

### PF-02: Replace QGrid Eight-Way Positive-Octant Search

Status: implemented on 2026-06-04.

Original finding: `qgrid_store()` looped over all eight symmetry projections
for every sampled point, but the comment said the test passes only once per
point.

Evidence:

- `intrinsic_qgrid.f90` now calls
  `qgrid_positive_octant_projection_index(...)` once per sampled point.
- The helper uses table-driven mappings to return the exact projection slot
  previously selected by the first successful loop iteration.
- Non-rotating models preserve all eight sign combinations.
- Rotating models preserve the old four-fold/eight-slot convention: only slots
  1, 3, 5, and 7 can be selected because the old rotating position-sign table
  duplicated slots in pairs.
- Boundary behavior is preserved: points with `x == 0` or `z == 0` are not
  stored; non-rotating `y == 0` uses the positive-y sign slot; rotating
  `y == 0` follows the sign of `x`.

Implementation: compute the needed projection index directly from the signs of
`x`, `y`, and `z`, then apply the existing position and velocity sign rows once.
The old `psgn1`, `psgn2`, `vsgn1`, and `vsgn2` tables remain the source of
truth for coordinate and velocity sign application.

Potential payoff: medium to high inside qgrid work. It removes up to seven
failed branch tests and sign multiplications per sampled point. Total-run
payoff depends on how much time is qgrid versus DOP853 integration.

Risk after implementation: medium in general because symmetry conventions
affect scientific output. The normal non-rotating fixture now checks both LOSVD
and full intrinsic qgrid moments against generated reference data. A dedicated
rotating-frame qgrid fixture is still needed before treating the `Omega /= 0`
path as scientifically regression-tested.

### PF-03: Precompute Sign Tables Once Per Setup

Status: implemented on 2026-06-04.

Original finding: both `qgrid_store()` and `project_n()` declared full sign
tables, assigned `vsgn=vsgn1`, `psgn=psgn1`, and branched on `Omega` inside
routines that are called repeatedly.

Evidence:

- `projection.f90` now stores the non-rotating and rotating projection sign
  tables as module-level parameters.
- `projection_setup()` now selects `projection_psgn` and `projection_vsgn`
  once from `Omega`.
- `project_n()` no longer imports `Omega`, declares full sign tables, or copies
  selected sign arrays.
- `intrinsic_qgrid.f90` now stores the non-rotating and rotating qgrid sign
  tables as module-level parameters.
- `qgrid_setup()` now selects `qgrid_psgn`, `qgrid_vsgn`, and
  `qgrid_rotating_frame` once from `Omega`.
- `qgrid_store()` no longer imports `Omega`, declares full sign tables, or
  copies selected sign arrays.

Implementation: selected sign tables are module state in their existing
modules. No new shared module was introduced, so the change avoids build-order
and interface churn while removing the per-call setup work. The existing sign
values were moved, not changed.

Potential payoff: low to medium. The table copies are small, but the calls are
frequent. This is mostly cleanup that removes avoidable work and reduces the
chance of inconsistent sign-table edits.

Risk after implementation: low/medium. Normal non-rotating generated qgrid and
LOSVD parity tests cover the active fixture. A dedicated rotating-frame fixture
is still needed before treating the `Omega /= 0` sign-table path as
scientifically regression-tested.

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

Checked result, 2026-06-04: SciPy `FortranFile` cannot directly replace the
temporary files with `io.BytesIO` or `bz2.BZ2File`.

- `FortranFile.__init__` accepts objects with `.seek`.
- `FortranFile.read_record()` still calls `np.fromfile(self._fp, ...)`.
- `io.BytesIO` fails because it has no real file descriptor.
- `bz2.BZ2File` has a file descriptor, but `np.fromfile()` reads compressed
  bytes from the underlying descriptor rather than decompressed bytes, corrupting
  Fortran record markers.

Feasible alternative: a small custom Fortran-record reader that uses
`file.read(n)` and `np.frombuffer(...)` can stream from `bz2.open(...)`
correctly. A synthetic check with default-qgrid-sized records verified
correctness. On a 36.9 MB raw / 0.68 MB `.bz2` synthetic file, the current
temp-file path was slightly faster in a local micro-benchmark:

```text
temp bunzip2 + scipy FortranFile: best ~2.15 s
streaming bz2 + custom reader:   best ~2.40 s
```

Improvement: do not replace this blindly. If disk churn or temp-file collisions
become a practical problem, prototype a small internal record reader behind
tests and benchmark it on real DYNAMITE `datfil/` outputs. This is more about
temporary disk use and shell/subprocess cleanup than guaranteed wall-time
improvement.

Potential payoff: low to medium, depending on output size, filesystem, and
whether avoiding temporary files matters more than raw read speed.

Risk: medium. A custom reader must exactly preserve Fortran record-marker
handling, mixed-record reads, dtype behavior, EOF/error behavior, and large-file
performance. Do not replace without tests on large real files.

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

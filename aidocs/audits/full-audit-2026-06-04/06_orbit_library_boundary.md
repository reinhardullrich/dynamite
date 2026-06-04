# 06 Orbit Library Boundary

Audit date: 2026-06-04

## Scope

Python-to-Fortran orbit-library handoff, direct shared-library ABI, qgrid/LOSVD
outputs, compression/readback, reader compatibility, and current tests.

## Current State

The active non-bar orbit-library runtime is the direct shared-library backend
in `dynamite/orblib_api.py`. It passes model inputs, orbit starts, PSF,
aperture, histogram, and binning arrays directly to
`liborblib_fortran.so`. It no longer creates Fortran `infil/` files for the
active path.

## Findings

### OB-001 - Direct backend output publication is not fully transactional

Severity: Medium.

- raw `.dat` files are written by Fortran directly to final names;
- done marker files are touched after compression, but there is no full output
  manifest with sizes, hashes, ABI version, and generation parameters.

Recommendation: add a versioned output manifest and validate all output files
before touching done markers.

### OB-002 - Python readers still decompress `.bz2` to temporary `.dat` files

Severity: Low/Medium.

Evidence:

- `dynamite/orblib.py` still uses `bunzip2 -c ... > tmpfname` before
  `scipy.io.FortranFile` reads qgrid, LOSVD, and pops data.

Checked result:

- SciPy `FortranFile` cannot directly read `io.BytesIO`/`bz2.BZ2File` safely
  because `np.fromfile()` needs a real file descriptor and would see compressed
  bytes for `bz2.BZ2File`.

Recommendation: keep current path for correctness unless a custom Fortran
record reader is added with real large-file tests.

### OB-003 - Active direct backend currently supports only non-bar triaxial path

Severity: Medium.

Evidence:

- `_direct_orblib_inputs()` raises `NotImplementedError` for bar/disk systems.

Recommendation: keep this explicit hard error until bar/rotating direct-input
fixtures exist.

### OB-004 - Rotating-frame parity fixture is missing for symmetry-sensitive Fortran paths

Severity: Medium scientific sensitivity.

The active tests use a non-rotating fixture. There is still no real
`Omega /= 0` rotating-frame output fixture for qgrid/projection/orbit-class
behavior.

Recommendation: add a minimal rotating-frame fixture before further symmetry or
sign-table changes.

### OB-005 - `dynamite/orblib.py` still contains shell-script execution paths

Severity: Medium.

`dynamite/orblib.py` still has generated shell scripts and subprocess handling.
Those paths remain in the package.

Recommendation: either clearly mark these paths as inactive compatibility code
or remove them once the direct backend covers all supported cases.

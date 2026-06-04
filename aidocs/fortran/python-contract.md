# Python Contract For The Fortran Backend

Last updated: 2026-06-04

Purpose: exact agent-facing map of how Python calls the active Fortran
orbit-library backend.

## Current Contract Summary

Active Python facade:

```text
dynamite/orblib_api.py
```

Active Fortran shared library:

```text
orblib_fortran/build/lib/liborblib_fortran.so
```

Build command:

```bash
make -C orblib_fortran shared
```

Backend name:

```text
fortran_shared_library
```

Shared-library ABI version:

```text
2
```

Python checks the ABI through `orblib_api_abi_version()` before making backend
calls. If the ABI changes, update both:

- `SHARED_LIBRARY_ABI_VERSION` in `dynamite/orblib_api.py`.
- `orblib_api_abi_version()` in
  `orblib_fortran/source/orblib_c_api.f90`.

## Python Public Entry Points

Primary request/result API:

- `dynamite.orblib_api.OrbitLibraryRequest`
- `dynamite.orblib_api.OrbitLibraryResult`
- `dynamite.orblib_api.run_orbit_library()`
- `dynamite.orblib_api.SharedLibraryFortranOrbitBackend`
- `dynamite.model.Model.run_orblib_api()`

Legacy-compatible model path:

- `dynamite.model.Model.get_orblib()`
- `dynamite.orblib.LegacyOrbitLibrary.get_orblib()`
- `dynamite.orblib.LegacyOrbitLibrary.read_losvd_histograms()`
- `dynamite.orblib.LegacyOrbitLibrary.read_orbit_base()`
- `dynamite.orblib.LegacyOrbitLibrary.read_orbit_intrinsic_moments()`
- `dynamite.orblib.LegacyOrbitLibrary.read_orbit_property_file()`

`LegacyOrbitLibrary` is still the active reader/adapter object. The word
`Legacy` here does not mean the backend is unused. It means the class preserves
the historical orbit-library file contract and Python reader behavior.

## Normal Model Call Graph

```text
Model.setup_directories()
  creates <model>/ and <model>/datfil/

Model.get_orblib()
  creates LegacyOrbitLibrary
  calls LegacyOrbitLibrary.get_orblib()

LegacyOrbitLibrary.get_orblib()
  creates SharedLibraryFortranOrbitBackend
  calls backend.generate_orbit_library(self)

SharedLibraryFortranOrbitBackend.generate_orbit_library()
  checks datfil/tube_box_done
  rejects LegacyWeightSolver
  checks liborblib_fortran.so exists
  creates datfil/
  runs orbit-start generation in memory
  runs tube orbit library with direct arrays
  runs box orbit library with direct arrays
  calculates intrinsic masses in Python
  touches datfil/tube_box_done if tube and box markers exist
```

The request/result API path wraps the same file-producing backend:

```text
Model.run_orblib_api()
  -> OrbitLibraryRequest.from_model(...)
  -> run_orbit_library(request)
  -> SharedLibraryFortranOrbitBackend.run(request)
  -> LegacyOrbitLibrary readers
  -> OrbitLibraryResult
```

## Active Shared-Library Calls

### `orblib_api_run_orbitstart_memory`

Purpose: generate orbit-start tables for tube and box orbit-library runs.

Fortran implementation:

```text
orblib_fortran/source/orblib_c_api.f90
```

Python caller:

```text
SharedLibraryFortranOrbitBackend.run_orbitstart_memory()
```

Fortran internal flow:

```text
orblib_api_run_orbitstart_memory
  -> iniparam_from_arrays(...)
  -> ip_setup(...)
  -> runorbitstart_memory(...)
  -> ip_stop()
```

Important inputs:

- random seed
- MGE arrays:
  - surface brightness in physical units
  - observed Gaussian sigma in arcsec
  - observed flattening
  - observed position angle
- distance
- viewing angles
- mass-to-light
- black-hole mass
- potential softening
- orbit grid:
  - `nener`
  - `rlogmin`
  - `rlogmax`
  - `ni2`
  - `ni3`
  - `dithering`
- intrinsic qgrid dimensions
- dark-halo type and parameters
- maximum output rows

Important outputs:

- tube begin table
- box begin table
- tube `noreg` flags
- box `noreg` flags
- row counts
- status code

The begin tables have 9 columns:

```text
x y z vx vy vz rcirc tcirc vcirc
```

### `orblib_api_run_orblib_direct`

Purpose: run one orbit-library part from Python-owned arrays and write the
binary `datfil/` outputs.

Fortran implementation:

```text
orblib_fortran/source/orblib_c_api.f90
```

Python caller:

```text
SharedLibraryFortranOrbitBackend._run_orbit_library_part_direct()
```

Fortran internal flow:

```text
orblib_api_run_orblib_direct
  -> iniparam_from_arrays(...)
  -> setup_direct(...)
  -> run()
  -> stob()
  -> ip_stop()
```

Python calls this twice for a normal model:

- `orblib`: tube orbit library.
- `orblibbox`: box orbit library.

Important direct inputs:

- model potential arrays and scalars
- begin table from `orblib_api_run_orbitstart_memory`
- begin `noreg` flags
- integration time and sampling controls
- PSF Gaussian tables
- aperture metadata
- spatial binning maps
- LOSVD histogram definitions
- direct output paths

Important output paths per file root:

```text
datfil/<root>_qgrid.dat
datfil/<root>_pops.dat
datfil/<root>_losvd_hist.dat
datfil/<root>.dat_orbclass.out
```

## Direct ABI Array Rules

Python passes raw `ctypes` pointers into Fortran. Treat the following as
contractual unless all call sites, Fortran dummy arguments, tests, and fixtures
are updated together.

- Numeric arrays are contiguous `float64` or `int32` unless the existing
  declaration says otherwise.
- 2D matrices that Fortran indexes by column-major layout must be Fortran-order
  arrays on the Python side.
- Paths are encoded as character buffers plus lengths, not as filesystem state
  discovered by Fortran.
- The begin table shape is `(begin_rows, 9)`.
- The direct backend sends Python-owned PSF, aperture, histogram, and binning
  arrays; it does not create the legacy Fortran `infil/` input files.

High-risk ABI changes:

- changing dummy argument order
- changing scalar kind or integer width
- changing string-length handling
- changing 2D array layout
- changing begin-row shape
- changing status-code semantics
- changing output path interpretation

## Direct Backend Scope

The active direct shared-library backend supports the normal non-bar triaxial
path. The direct input builders reject unsupported bar/disk paths before
calling Fortran.

Bar-related Fortran routines and old executable drivers still exist in retained
source files, but the direct Python ABI does not expose a complete active bar
workflow.

## Worker Process Isolation

Default Python setting:

```text
isolate_fortran_calls=True
```

This is intentional. The Fortran backend uses global module state and old-style
error exits. Running it directly in the Python interpreter is risky because a
Fortran `stop`, memory fault, or retained module state can terminate or poison
the Python process.

Default call topology:

```text
Python parent process
  -> orbit-start worker process
  -> tube worker process
  -> box worker process
```

Do not disable process isolation for production or parity tests unless the test
is specifically about in-process ABI behavior.

## Working Directory Contract

The Fortran interpolation cache is named:

```text
interpolgrid
```

It is a bare file name inside the current working directory. The Python backend
runs workers in the model directory so orbit-start, tube, and box workers share
the same `interpolgrid` for one model.

Important consequences:

- `interpolgrid` is model-local by convention, not by an explicit path
  argument.
- It is not content-addressed by model hash.
- Running multiple different orbit-library jobs in the same model directory is
  not safe unless cache and output races are handled explicitly.
- Parallelism should happen across different model directories, not by
  launching multiple writers into one `datfil/` directory.

## Precision Compatibility

The direct shared-library path intentionally preserves parts of the old text
interface precision because the generated orbit library is numerically
sensitive.

Python quantizes direct `parameters_pot` values before calling the Fortran ABI:

- MGE surface brightness: 2 decimals.
- observed sigma: 5 decimals.
- observed flattening: 5 decimals.
- observed position angle: 2 decimals.
- viewing angles: 9 decimals.

Fortran `integrator_setup_direct()` round-trips begin rows through the legacy
format:

```text
9ES30.10
```

Do not remove these compatibility steps without regenerating fixtures and
checking scientific parity. The old executable path encoded these roundings
through text files, so exact in-memory values can change the final LOSVD mass
distribution.

## Solver Boundary

The active weight-solver path is Python `NNLS`. The archived Fortran
NNLS/GALAHAD code is not part of the active build.

The Fortran orbit-library backend produces orbit matrices and metadata. It does
not solve the final non-negative least-squares weight problem in the active
workflow.

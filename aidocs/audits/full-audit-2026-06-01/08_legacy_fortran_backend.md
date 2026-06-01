# 08 Legacy Fortran Backend Audit

Scope: `legacy_fortran/` build scripts, Linux build notes, orbit integration
entry points, mass-bin code, triaxial potential routines, and the legacy NNLS /
GALAHAD solver path.

Commands/checks run:

```bash
gfortran --version
make -n nogal
make nogal
cd galahad-2.3 && ./install_galahad
make GALAHADDIR=/home/reinhard/projects/thomas/dynamite/legacy_fortran/galahad-2.3 GALAHADTYPE=pc.lnx.gfo/double all
ldd triaxnnls_CRcut triaxnnls_noCRcut triaxnnls_bar
nm -u triaxnnls_CRcut triaxnnls_noCRcut triaxnnls_bar
```

Observed environment:

- GNU Fortran 13.3.0 is available at `/usr/bin/gfortran`.
- `make nogal` succeeds locally and builds the no-GALAHAD orbit executables.
- Local vendored dependency trees exist for GALAHAD, CUTEr, and HSL.
- The full `make all` target succeeds after repairing generated GALAHAD static
  archives that omitted `gltr.o` and `hsl_ma57d.o`.
- Direct solver-mode `5` runtime probes reached GALAHAD/QPB and logged
  `QPB_solve exit status = -5` while the shell process still exited `0`.

## Findings

### FB-001 - Medium - full legacy solver build is fragile even with local vendored inputs

Evidence:

- `legacy_fortran/README.linux:4-21` requires `DYNAMITE`, `FORTRAN`,
  `HSLARCHIVE`, and `GALAHADDIR`, then runs `./compile_deps.sh`, applies
  `linux.patch`, and builds with `Makefile.linux`.
- `legacy_fortran/compile_deps.sh:6-20` exits unless those environment
  variables and the HSL archive are present.
- `legacy_fortran/compile_deps.sh:22-35` clones ARCHDefs, CUTEst, SIFDecode,
  and GALAHAD from GitHub into `legacy_fortran/`.
- `legacy_fortran/Makefile:88-98` defaults to `GALAHADDIR=$(CURDIR)/galahad-2.3`
  and a macOS GALAHAD type, while `Makefile.linux` uses `pc.lnx.gfo/double`.
- This checkout already contains `legacy_fortran/galahad-2.3`,
  `legacy_fortran/cuter`, and `legacy_fortran/hsl`.
- After running the local GALAHAD installer, the first full `make all` attempt
  failed because `libgalahad.a` lacked `gltr.o` and `libgalahad_hsl.a` lacked
  `hsl_ma57d.o`.
- Re-adding those generated objects to the local archives with `ar`/`ranlib`
  allowed the full build to succeed.

Impact:

The local no-GALAHAD build is reproducible with the system compiler, but the
full legacy NNLS/GALAHAD build is not a clean one-command path. Fresh builds can
produce compiled modules while still leaving required object members out of the
static archives, causing final link failures.

Recommended fix:

Document two explicit build modes:

1. `make nogal`: orbit integration only, currently locally reproducible.
2. full GALAHAD build: requires local GALAHAD/CUTEr/HSL setup, archive-member
   verification, and a documented repair or Makefile fix.

Add a preflight script that checks required paths and prints exact next steps
without starting long downloads or compilation. The preflight should also
verify that `libgalahad.a` contains `gltr.o` and `libgalahad_hsl.a` contains
`hsl_ma57d.o`.

### FB-002 - Medium - optimized flags reduce portability and reproducibility

Evidence:

- `legacy_fortran/Makefile:57-85` uses `-ffast-math -O3 -march=native
  -fomit-frame-pointer -m64 -funroll-loops -ftree-loop-linear -std=legacy`.
- `legacy_fortran/Makefile.linux:64-92` uses the same optimization profile.

Impact:

`-march=native` produces binaries tuned to the local CPU and may not run or
behave identically elsewhere. `-ffast-math` allows floating-point
transformations that can change edge-case numerical behavior. For performance
runs this may be intentional, but it is not ideal for reproducibility,
debugging, or audit baselines.

Recommended fix:

Add a documented reproducible/debug build mode that removes `-march=native` and
`-ffast-math`, enables bounds/runtime checks, and can be used for CI or
scientific verification runs.

### FB-003 - High - CI and local no-GALAHAD build do not exercise mass or legacy solver executables

Evidence:

- `legacy_fortran/Makefile:101-102` defines `all` as orbit, mass, and NNLS
  executables, but `nogal` only builds orbit executables.
- `legacy_fortran/Makefile.linux:104-105` has the same split.
- The local `make nogal` run built `orbitstart`, `orbitstart_bar`,
  `orblib_new_mirror`, and `orblib_bar` only.

Impact:

The locally verified build does not cover `triaxmass`, `triaxmassbin`, or the
legacy NNLS solver executables. Since the Python runtime can depend on these
executables for model output, this leaves an important backend class unverified.

Recommended fix:

Create a minimal Fortran smoke-test matrix:

- no-GALAHAD orbit executable build;
- mass executable build;
- optional GALAHAD solver build when local HSL/GALAHAD prerequisites exist.

### FB-004 - High - backend failure signaling is not reliable enough for Python wrappers

Evidence:

- Many Fortran routines use `stop` for validation and runtime errors, for
  example `legacy_fortran/triaxpotent.f90:129-150`,
  `legacy_fortran/triaxmassbin_f.f90:247-267`, and
  `legacy_fortran/triaxnnls_CRcut.f90:765`.
- The Python wrappers found in the orbit-library and weight-solver audit
  sections currently infer success primarily from captured stdout or touched
  marker files rather than subprocess return codes.

Impact:

Even when the Fortran executable exits non-zero, the Python layer can misclassify
the run if the surrounding shell script creates completion markers or if stdout
handling masks the failure. This is a cross-boundary correctness risk.

Recommended fix:

Make the Python wrappers check subprocess `returncode`, required output files,
and expected file sizes before marking a run complete. Generated shell scripts
should use `set -e` and touch completion files only after all outputs validate.

### FB-005 - Medium - integration warnings are printed but do not fail the run

Evidence:

- `legacy_fortran/triaxpotent.f90:523-525`, `551-553`, `558-560`, and
  `565-567` print `dqxgs` integration errors but continue.
- `legacy_fortran/triaxmassbin_f.f90:81-85` treats some integration statuses as
  warnings rather than fatal errors.

Impact:

Potential or mass calculations can continue after numerical integration
warnings. That may be appropriate for recoverable quadrature statuses, but the
Python side currently has no structured way to distinguish harmless warnings
from output that should be rejected.

Recommended fix:

Classify integration statuses explicitly. At minimum, emit a machine-readable
summary file with warning counts and maximum error status, and require Python to
record those statuses in the model table.

### FB-006 - Medium - hard-coded aperture mass buffer can stop large models at runtime

Evidence:

- `legacy_fortran/triaxmassbin_f.f90:19` defines
  `global_apermass` as `dimension(400_i4b**2*6)`.
- `legacy_fortran/triaxmassbin_f.f90:263-267` stops if the requested range
  exceeds that static array.

Impact:

Large aperture/bin configurations can pass Python-side setup but fail later
inside Fortran. The failure threshold is implicit and is not preflighted before
launching backend jobs.

Recommended fix:

Compute the required aperture-mass storage size on the Python side before
launching `triaxmassbin`, or allocate the Fortran array dynamically from input
dimensions.

### FB-007 - Low - uninitialized variable is printed in mass-bin reader

Evidence:

- `legacy_fortran/triaxmassbin_f.f90:230-237` declares `i` and prints it before
  any assignment in `read_binningfile`.
- `legacy_fortran/Makefile.linux:21` enables `-Wuninitialized`, but the default
  `Makefile` does not.

Impact:

This is probably diagnostic-only, but it is still undefined behavior and can
make logs misleading.

Recommended fix:

Initialize `i` or remove it from the diagnostic print.

### FB-008 - Medium - non-positive random seeds intentionally produce stochastic orbit-library seeds

Evidence:

- `legacy_fortran/orblibprogram.f90:43-54` reads a seed and uses a stochastic
  seed whenever the input value is `<= 0`.

Impact:

This is documented in the source comment, but it is a reproducibility footgun
for audit runs. If a config leaves the seed at zero or negative, repeated runs
will not be bitwise reproducible.

Recommended fix:

For audit and regression runs, require positive seeds and record the seed in the
model metadata.

### FB-009 - Medium - GALAHAD failure status is printed but not made fatal

Evidence:

- `legacy_fortran/triaxnnls_CRcut.f90:1139-1145` calls `QPB_solve`; if
  `info%status` is non-zero, it prints the exit status but does not stop before
  continuing cleanup and output flow.
- Direct local solver-mode `5` runtime probes for `triaxnnls_noCRcut` and
  `triaxnnls_CRcut` both reached GALAHAD/QPB and logged:

```text
QPB_solve exit status =     -5
```

- The same logs reported an infeasible problem and `Error return -5 from
  LSQP_solve`, then continued to `Making predictions` and wrote output files.
- Both direct commands exited with shell status `0`.

Impact:

A failed GALAHAD solve can continue far enough that the surrounding process may
look successful unless downstream output validation catches it. This is now a
confirmed runtime behavior, not only a static-code concern.

Recommended fix:

Treat non-zero GALAHAD status as a hard solver failure, or map accepted
non-zero statuses to explicit warning states that Python records and validates.

## Local Status

The no-GALAHAD backend compiled successfully in this repository.

The full GALAHAD-backed backend also compiled locally after generated archive
repair. Link/load checks passed for `triaxnnls_CRcut`, `triaxnnls_noCRcut`, and
`triaxnnls_bar`.

The noCRcut and CRcut GALAHAD/QPB runtime paths were reached with generated
model input. Both returned GALAHAD status `-5` but process exit code `0`, so
the remaining high-priority issue is solver-status propagation and output
validation, not just compilation.

The barred GALAHAD solver binary was build/link/smoke checked, but it was not
run with a bar-specific model input in this follow-up.

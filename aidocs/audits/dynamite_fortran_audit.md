# DYNAMITE Fortran Audit

Date: 2026-06-01

Repository audited: `/home/reinhard/projects/thomas/dynamite`

Current-status update, 2026-06-02: this earlier standalone audit has been
adapted for the `fortran-cleanup` branch. The active Fortran backend is now
`orblib_fortran/`, normal builds produce only
`orblib_fortran/build/lib/liborblib_fortran.so`, and Python calls it through
`dynamite/orblib_api.py`. Legacy NNLS/GALAHAD solver sources and `triaxmass*`
helpers are archived under `archive/legacy_nnls_fortran/`; `orbgen`/`partgen`
are archived under `archive/legacy_orbgen_partgen/`. Findings about active
legacy solver executables, mass-helper executables, or executable packaging are
therefore resolved or obsolete unless explicitly marked as applying to the
archived tree.

This is a separate audit of the Fortran side of DYNAMITE. I focused on DYNAMITE-maintained Fortran entry points, the build system, the Python/Fortran file contract, and the integration with bundled numerical solvers. I did not line-by-line re-audit the entire vendored GALAHAD/CUTEr/HSL trees; those are treated as third-party dependencies and noted separately.

## Executive Summary

The Fortran code is legacy scientific Fortran with a lot of domain knowledge in it, but it has several reliability hazards that matter for production runs:

- Active shared-library calls are isolated in worker processes, but many legacy
  Fortran error paths still use plain `stop "message"` and can terminate the
  worker process. Python must continue treating a worker failure as fatal.
- Solver failure handling in the old GALAHAD/QPB and Fortran NNLS executables
  is now an archived-path concern because `LegacyWeightSolver` is rejected by
  current runtime configuration.
- Some orbit-start logic can consume uninitialized arrays if the integrator
  stores fewer crossing samples than expected.
- The active Makefiles now build only the shared library; previous findings
  about active mass/NNLS executable builds and executable packaging are
  obsolete.
- The archived GALAHAD/CUTEr/HSL numerical dependencies are still old and
  should remain outside the active runtime unless explicitly restored.

I would not treat the Fortran pipeline as robust until the high-severity findings below are fixed and covered by at least one end-to-end regression case.

## Scope

First-party or DYNAMITE-specific files reviewed:

- `orblib_fortran/Makefile`
- `orblib_fortran/Makefile.linux`
- `archive/legacy_nnls_fortran/legacy_fortran/compile_deps.sh`
- `orblib_fortran/source/iniparam_f.f90`
- `orblib_fortran/source/dmpotent.f90`
- `orblib_fortran/source/triaxpotent.f90`
- `orblib_fortran/source/interpolpotent.f90`
- `orblib_fortran/source/unused/orbitstart.f90`
- `orblib_fortran/source/unused/orbitstart_bar.f90`
- `orblib_fortran/source/orbitstart_f.f90`
- `orblib_fortran/source/unused/orblibprogram.f90`
- `orblib_fortran/source/unused/orblibprogram_bar.f90`
- `orblib_fortran/source/orblib_f_new_mirror.f90`
- `archive/legacy_nnls_fortran/legacy_fortran/mass_helpers/triaxmass_f.f90`
- `archive/legacy_nnls_fortran/legacy_fortran/mass_helpers/triaxmassbin_f.f90`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_CRcut.f90`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_bar.f90`
- `archive/legacy_orbgen_partgen/legacy_fortran/orbgen_partgen/orbgen.f90`
- `archive/legacy_orbgen_partgen/legacy_fortran/orbgen_partgen/partgen.f90`
- `orblib_fortran/source/ran1_nr.f`

Vendored or mostly third-party code noted but not fully re-reviewed:

- `archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/`
- `archive/legacy_nnls_fortran/legacy_fortran/cuter/`
- `archive/legacy_nnls_fortran/legacy_fortran/hsl/`
- numerical helper routines under `archive/legacy_nnls_fortran/legacy_fortran/sub/`

## Build And Verification Checks Performed

- Confirmed local compiler: `gfortran 13.3.0`.
- Original pre-cleanup check: ran `make -n nogal` in `legacy_fortran`; this
  dry-run emitted plausible commands for `orbitstart`, `orbitstart_bar`,
  `orblib_new_mirror`, and `orblib_bar`. Current `make nogal` in
  `orblib_fortran/` builds the shared library.
- Original archived-solver check: ran `make -n all` in `legacy_fortran`; this
  dry-run showed the NNLS/GALAHAD targets still used
  `galahad-2.3/modules/mac.osx.gfo/double/` and
  `objects/mac.osx.gfo/double/` from the default Makefile.
- Original Linux-Makefile check: ran `make -n -f Makefile.linux nogal`; because
  `FORTRAN` was unset, commands expanded to a leading compiler flag instead of
  a compiler, e.g. `Wuninitialized ...`.
- Compiled a tiny `/tmp` program with the same optimization flags to confirm the current gfortran accepts the flags.
- Tested `stop "bad"` with local gfortran; it printed `STOP bad` and exited with status code `0`.
- Did not run full `make all`, because that would write objects/binaries into the clone and depends on GALAHAD/HSL setup that is not currently configured.

The cloned repo remained clean after the audit (`git status --short` produced no output).

## Findings

### 1. Plain Fortran `stop "message"` Can Exit Successfully

Severity: High

Examples:

- `orblib_fortran/source/dmpotent.f90:41`
- `orblib_fortran/source/triaxpotent.f90:130`
- `orblib_fortran/source/triaxpotent.f90:714`
- `orblib_fortran/source/orblib_f_new_mirror.f90:2459`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:141`
- `archive/legacy_nnls_fortran/legacy_fortran/mass_helpers/triaxmass_f.f90:197`

The code uses many `stop "message"` statements for real error conditions: invalid models, failed integrators, inconsistent orbit libraries, malformed input, and disk-write errors.

With the local compiler:

```text
STOP bad
exit code: 0
```

That means a failed Fortran executable may look successful to Python, shell scripts, CI, or workflow runners. This is especially risky because the Python side launches shell scripts and relies on process status and output files.

Recommended fix:

- Replace fatal `stop "message"` paths with `error stop 1` or `stop 1` plus a preceding `write(error_unit,*)`.
- Add a small fatal helper using `iso_fortran_env, only: error_unit`.
- Make generated shell scripts use `set -euo pipefail` and redirect both stdout and stderr into logs.
- Add tests that intentionally trigger an input error and assert the executable exits nonzero.

### 2. GALAHAD/QPB Failure Status Is Ignored Before Writing Weights

Severity: High

Primary example:

- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:1144-1150`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:1166-1169`

The code calls `QPB_solve`, prints `info%status` when nonzero, but then continues and assigns:

```fortran
orbweight(:) = p%X(:)
```

The same pattern is present in the bar and CRcut variants. If GALAHAD returns an error, the code can still write `_nnls.out`, `_con.out`, `_orb.out`, and kinematic predictions using a failed or partial solution.

Recommended fix:

- Treat every nonzero `info%status` as fatal unless there is a documented recoverable subset.
- Do not call `allpred()` or write orbit weights after solver failure.
- Store solver status in the output metadata.
- Add a regression test with an intentionally infeasible or malformed fit to confirm the program exits nonzero and does not write final-looking outputs.

### 3. NNLS Failure Mode Is Printed But Not Enforced

Severity: High

Examples:

- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:779-785`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:1242-1254`

The Lawson-Hanson `nnls` call returns `mode`, but the program only prints it. Standard NNLS semantics are that `mode = 1` is success; other modes indicate invalid dimensions or iteration failure. The code continues regardless.

Recommended fix:

- Check `mode == 1` after every `nnls` call.
- Use a fatal nonzero exit when `mode /= 1`.
- Include the mode and residual in a structured output file only after successful completion.

### 4. `findtubeorbitwidth` Can Use Uninitialized Positions

Severity: High

Relevant code:

- `orblib_fortran/source/orbitstart_f.f90:657`
- `orblib_fortran/source/orbitstart_f.f90:704-717`
- `orblib_fortran/source/orbitstart_f.f90:720-731`
- `orblib_fortran/source/orbitstart_f.f90:783-818`

`findtubeorbitwidth` allocates `pos_t(intsteps, 3)`, the DOP853 callback stores plane crossings, and then the caller computes `rad(:)` over the entire `pos_t` array.

The callback has an internal `count`, but that count is not returned to `findtubeorbitwidth`. If fewer than `intsteps` crossings are stored, the tail of `pos_t` is uninitialized and `maxval/minval` can use garbage values when computing `tube`.

Recommended fix:

- Initialize `pos_t = 0.0_dp` immediately after allocation.
- Return the filled count through `IPAR` or a module variable.
- Compute `rad(1:count)` only.
- Treat `count == 0` or `count < expected_minimum` as an integration failure.
- Build this file in debug mode with `-fcheck=all -finit-real=snan` to flush this out.

### 5. The Linux Makefile Is Broken Unless `FORTRAN` Is Passed

Severity: High

Relevant code:

- `orblib_fortran/Makefile.linux:13-14`
- `orblib_fortran/Makefile.linux:90-92`

`Makefile.linux` sets `compilername=gfortran`, but the actual compile commands use `$(FORTRAN)`. The default `FORTRAN=path/to/gfortran` line is commented out.

The dry-run confirms that without `FORTRAN=...`, commands begin with a compiler flag:

```text
Wuninitialized -ffast-math -O3 ...
```

This is worse than just "compiler not found": because the expanded command originally starts with `-Wuninitialized`, GNU make treats the leading `-` as "ignore errors" syntax for the recipe line.

Recommended fix:

- Set `FORTRAN ?= gfortran`.
- Prefer standard variables: `FC ?= gfortran`, `FFLAGS += ...`.
- Add an explicit make-time check that `$(FC)` is not empty.
- Run `make -f Makefile.linux nogal` in CI.

### 6. Default `make all` Points GALAHAD At macOS Paths

Severity: High for Linux users building NNLS/GALAHAD targets

Relevant code:

- `archive/legacy_nnls_fortran/legacy_fortran/Makefile:89-98`
- `archive/legacy_nnls_fortran/legacy_fortran/Makefile:262-288`

The default Makefile sets:

```make
GALAHADTYPE= mac.osx.gfo/double/
```

On Linux, `make all` still emits compile/link commands using:

```text
archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/modules/mac.osx.gfo/double/
archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/objects/mac.osx.gfo/double/
```

CI only runs `make nogal`, so this breakage is not covered.

Recommended fix:

- Detect OS/compiler or require `GALAHADTYPE` explicitly for `make all`.
- Fail early if `$(GALAHADDIR)/modules/$(GALAHADTYPE)` or `objects/$(GALAHADTYPE)` is missing.
- Add a CI job that at least dry-runs, and ideally builds, the NNLS/GALAHAD targets.

### 7. Solver Dependency Versions Are Very Old Or Pinned Old

Severity: Medium to High, depending on whether NNLS/GALAHAD targets are required

Local state:

- `archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/version` says `GALAHAD version 2.2.0003 (12/June/2008 16:45 GMT)`.
- `archive/legacy_nnls_fortran/legacy_fortran/cuter/README` references CUTEr documentation from 2003 and 2005.
- HSL files show versions and dates around 2004-2008.
- `archive/legacy_nnls_fortran/legacy_fortran/compile_deps.sh` pins:
  - ARCHDefs `v2.0.4`
  - CUTEst `v2.0.3`
  - SIFDecode `v2.0.3`
  - GALAHAD `v4.0.0`

Current upstream releases checked on 2026-06-01:

- GALAHAD latest release: `v5.4.0`, 2025-11-27, on GitHub.
- CUTEst latest release: `v2.7.0`, 2026-05-31, on GitHub.
- SIFDecode latest release: `v3.1.1`, 2026-05-16, on GitHub.
- ARCHDefs latest release: `v2.2.19`, 2025-10-28, on GitHub.

Sources:

- https://github.com/ralna/GALAHAD
- https://github.com/ralna/CUTEst
- https://github.com/ralna/SIFDecode
- https://github.com/ralna/ARCHDefs

Recommended fix:

- Decide whether the project supports the vendored 2008-era GALAHAD or the newer `compile_deps.sh` path.
- Remove one path or document both explicitly.
- Upgrade in a branch with numerical baselines, because optimizer changes can alter fitted weights.
- Pin by immutable commit SHA, not only branch/tag name, if reproducibility matters.

### 8. `compile_deps.sh` Is Fragile Around Paths And Failures

Severity: Medium

Relevant code:

- `archive/legacy_nnls_fortran/legacy_fortran/compile_deps.sh:6-12`
- `archive/legacy_nnls_fortran/legacy_fortran/compile_deps.sh:22-36`
- `archive/legacy_nnls_fortran/legacy_fortran/compile_deps.sh:38-65`

The script has some checks, but it does not use `set -euo pipefail`, and most path variables are unquoted:

```bash
cd ${DYNAMITE}/legacy_fortran
[ -a $HSLARCHIVE ] && tar -xf $HSLARCHIVE
make -f ../makefiles/${VERSION} FORTRAN=${FORTRAN}
```

Paths with spaces or glob characters can break it. Network clones are also mutable operationally, even with tagged branches, unless the script verifies the fetched commit.

Recommended fix:

- Add `set -euo pipefail`.
- Quote all path expansions.
- Use `[[ -f "$HSLARCHIVE" ]]`.
- Pin and verify commit SHAs.
- Add a `--dry-run` or documented expected directory layout.

### 9. NFW/Hernquist/gNFW Dark-Halo Formulas Have Center Singularities

Severity: Medium to High

Current status: resolved locally. The old mass/NNLS executables are archived,
and the active Fortran build is shared-library-only.

Relevant code:

- `orblib_fortran/source/dmpotent.f90:172-176`
- `orblib_fortran/source/dmpotent.f90:237-247`
- `orblib_fortran/source/dmpotent.f90:255-258`
- `orblib_fortran/source/dmpotent.f90:203-208`
- `orblib_fortran/source/dmpotent.f90:288-295`

Several dark-matter profiles divide by `sqrt(d2)`, `d2`, or `dnorm`, where `d2 = x*x + y*y + z*z`. At exactly the origin, this can produce NaN/Inf even where the analytic limit is finite or well-defined.

Examples:

- NFW potential uses `... / sqrt(d2) * log(...)`.
- NFW acceleration uses `x/sqrt(d2) * t1 * (...)` with `t1 = ... / d2`.
- Hernquist acceleration uses `x/sqrt(d2) * acceleration_r`.
- gNFW potential/acceleration use `dnorm` divisions.

Recommended fix:

- Add explicit small-radius analytic limits.
- Guard `d2 == 0.0_dp` and near-zero `d2`.
- Add tests for `(0,0,0)` and very small radii for every dark-halo profile.

### 10. Two-Orbit-Library Grid Consistency Checks Are Disabled

Severity: Medium to High

Relevant code:

- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:172-180`
- Similar blocks exist in `triaxnnls_CRcut.f90` and `triaxnnls_bar.f90`.

The code reads the second orbit library's intrinsic-grid metadata but comments out the consistency check:

```fortran
!if ( smom1 /= smom2 .or. slr1 /= slr2 .or. sth1 /= sth2 .or. sph1 /= sph2 ) &
!     stop "  Intrinsic grid is not the same size as the other library"
```

It also does not compare the actual `quad_lr`, `quad_lth`, and `quad_lph` boundary arrays. If the two libraries differ, the fit can mix incompatible constraints.

Recommended fix:

- Reinstate dimension checks.
- Compare all boundary arrays with a numeric tolerance.
- Include these values in output metadata for traceability.

### 11. Fixed-Size Arrays Impose Silent Model Limits

Severity: Medium

Relevant code:

- `archive/legacy_nnls_fortran/legacy_fortran/mass_helpers/triaxmass_f.f90:189-197`
- `archive/legacy_nnls_fortran/legacy_fortran/mass_helpers/triaxmassbin_f.f90:17-19`
- `archive/legacy_nnls_fortran/legacy_fortran/mass_helpers/triaxmassbin_f.f90:263-267`

`triaxmass_f.f90` uses:

```fortran
real(kind=dp), dimension(10000) :: radmass
```

`triaxmassbin_f.f90` uses:

```fortran
real(kind=dp), private, dimension(400_i4b**2*6) :: global_apermass
```

Both eventually `stop` if the requested model is too large. That is better than memory corruption, but the caps are arbitrary and the failure may exit with code 0 because of finding 1.

Recommended fix:

- Allocate these arrays dynamically from input sizes.
- Check requested sizes before allocation.
- Use fatal nonzero exits on impossible sizes.

### 12. Input Parsing Lacks Defensive `iostat` Checks

Severity: Medium

Relevant code:

- `orblib_fortran/source/iniparam_f.f90:101-151`
- `orblib_fortran/source/iniparam_f.f90:209-283`
- `orblib_fortran/source/orblib_f_new_mirror.f90:640-660`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:409-416`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:481-499`

Most input files are opened and read without `iostat`. Missing files, truncated files, invalid numeric fields, negative sizes, and inconsistent values generally become runtime aborts rather than controlled errors.

Specific concerns:

- `iniparam_f.f90` allocates arrays from file-provided counts without validating positive values.
- It prints `softl_arcsec*conversion_factor/2.95_dp/xmbh`; `xmbh == 0` would divide by zero in the diagnostic.
- The barred-mode branch prints an error for invalid `decmposed`, but does not stop immediately; later code can proceed with uninitialized arrays.

Recommended fix:

- Wrap input reads in helper routines that include filename, expected field, line number when practical, and nonzero exit status.
- Validate all counts before allocation.
- Validate physical constraints before derived calculations.

### 13. `next_content_line` Does Not Skip Blank Lines And Truncates At 80 Characters

Severity: Medium

Relevant code:

- `orblib_fortran/source/triaxpotent.f90:708-719`

The helper skips lines whose first nonblank character is `#`, but it returns blank lines as content. Callers then do `read(string,*)`, which can fail unexpectedly if a config file contains blank lines.

It is also fixed at `character(len=80)`, while several filenames and input lines elsewhere use lengths of 256 or 512.

Recommended fix:

- Skip blank lines as well as comments.
- Increase line length or use deferred-length allocatable strings if supported.
- Return status instead of calling `stop`.

### 14. Interpolation Cache Is Not Self-Describing Enough

Severity: Medium

Relevant code:

- `orblib_fortran/source/interpolpotent.f90:292-320`

The `interpolgrid` cache stores dimensions and grid data, and then validates by testing acceleration accuracy against the current model. That is useful, but the file itself does not record model parameters, compiler, code version, floating format, or profile type.

The current validation may catch many stale caches, but the cache is still opaque and hard to diagnose. It also depends on random-sample testing in `ip_testaccuracy`.

Recommended fix:

- Store a small header with model parameters, profile type, grid sizes, code version/hash, and endianness marker.
- Make cache invalidation deterministic before falling back to accuracy testing.
- Write cache status into logs.

### 15. Unformatted Fortran Binary Files Are A Fragile Cross-Language Contract

Severity: Medium

Relevant code:

- `orblib_fortran/source/orblib_f_new_mirror.f90:2461-2475`
- `orblib_fortran/source/orblib_f_new_mirror.f90:2520-2539`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:126-150`
- Python readers covered in the Python audit use Fortran-style binary records.

The orbit-library files are compiler/runtime-specific unformatted sequential records. They are not self-describing and can vary by compiler record markers, endianness, and record-size conventions.

The output close path writes a dummy final record containing `" "` to several files. That may be part of the reader contract, but it is implicit and fragile.

Recommended fix:

- Document the binary format explicitly.
- Add magic/version records.
- Consider moving long-lived file exchange to HDF5, FITS, NetCDF, or another self-describing scientific format.
- At minimum, add reader tests with known small fixture files.

### 16. CI Does Not Exercise The Full Fortran Surface

Severity: Medium

Relevant code:

- `.github/workflows/ci.yml:47-49`
- `.github/workflows/ci.yml:57-63`

CI builds only `make nogal`, which excludes:

- `triaxmass`
- `triaxmass_bar`
- `triaxmassbin`
- `triaxmassbin_bar`
- `triaxnnls_CRcut`
- `triaxnnls_noCRcut`
- `triaxnnls_bar`
- GALAHAD linking

The artifact verification step only lists files and does not assert executable presence. The test step does not run `pytest`; it runs `archive/dev_tests/test_nnls.py` as a shell command.

Recommended fix:

- Add shared-library checks after build.
- Add archived-solver checks only if the old solver backend is deliberately
  restored.
- Run `python -m pytest` or execute test files through Python intentionally.
- Keep the active orblib shared-library LOSVD regression tests.

### 17. Optimization Flags Reduce Numerical Debbugability And Portability

Severity: Low to Medium

Relevant code:

- `orblib_fortran/Makefile:57-65`
- `orblib_fortran/Makefile.linux:64-72`

The default build uses:

```make
-ffast-math -O3 -march=native -fomit-frame-pointer -m64
-funroll-loops -ftree-loop-linear
```

For scientific code, `-ffast-math` can alter NaN/Inf handling and floating-point associativity. `-march=native` creates binaries tuned for the build machine, not portable deployment.

Recommended fix:

- Make a reproducible release profile without `-march=native`.
- Keep a debug/sanitize profile with `-fcheck=all`, `-finit-real=snan`, `-ffpe-trap=invalid,zero,overflow`, and no `-ffast-math`.
- Run critical tests under debug flags periodically.

### 18. Some Temporary Or Solver Files Use Fixed Global Names

Severity: Low to Medium

Relevant code:

- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:826`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:840`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut.f90:1828`

The solver path uses fixed filenames like `orbmat.gal`, `sol`, and `datfil/abel_orb.out`. Parallel runs in the same working directory can collide, and stale files can be mistaken for current solver outputs.

Recommended fix:

- Prefix all temporary files with the model/run identifier.
- Use scratch directories per run.
- Check file modification times or include run IDs in files.

### 19. Repository Contains Backup And Platform Metadata Files

Severity: Low

Found files:

- `archive/legacy_nnls_fortran/legacy_fortran/sub/nnls95.f~`
- `archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/sifdec/SifDec.medium.pc.lnx.g77/Makefile.bak`
- `archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/src/.DS_Store`
- `archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/src/icfs/.DS_Store`
- `archive/legacy_nnls_fortran/legacy_fortran/hsl/icfs/.DS_Store`

These are not necessarily runtime bugs, but they make source packaging noisier and can confuse audits.

Recommended fix:

- Remove backup/platform files from version control if they are not intentionally part of the distribution.
- Add `.gitignore` rules for editor backups and `.DS_Store`.

## Positive Notes

- Most DYNAMITE-owned `.f90` modules use `implicit none`.
- The orbit-library output code uses `iostat` for many write/close operations, especially around status and binary output files.
- The interpolation cache validates accuracy after loading and regenerates the grid if accuracy is not sufficient.
- There are explicit sanity checks for many physical/model conditions, even if their exit status handling needs improvement.
- The repo has a CI workflow that at least compiles the non-GALAHAD Fortran path on Python 3.11, 3.12, and 3.13.

## What Remains Unaudited

After the overview, Python audit, and this Fortran audit, these areas are still not fully audited:

- Full third-party numerical libraries: GALAHAD, CUTEr/CUTEst, HSL, NAG-derived routines, DOP853/DOPRI5 internals, and Numerical Recipes helpers were not line-by-line reviewed.
- Scientific correctness: I did not validate the astrophysical equations or compare generated orbit libraries against published/reference model outputs.
- Full runtime behavior: the original audit did not run a complete DYNAMITE
  model end to end through all Fortran executables; current active tests now
  include an opt-in slow shared-library LOSVD regression fixture.
- Full `make all`: the original audit did not compile the GALAHAD-dependent
  targets in this workspace; those targets are now archived.
- Cross-platform binary compatibility: I did not test generated orbit-library files across compilers, endianness, or record-marker variants.
- Performance and scaling: I did not profile large model runs or memory usage.
- License/legal status: I did not perform a formal license audit of bundled HSL/GALAHAD/CUTEr/Numerical Recipes-derived code.
- Documentation accuracy: I did not fully audit all docs, examples, and tutorials against the current code.
- Generated output semantics: I did not deeply validate every output file format consumed by downstream Python plotting/reporting code.

## Suggested Fix Order

1. Replace fatal `stop "message"` with nonzero exits and update shell/Python launchers to fail hard.
2. Keep archived GALAHAD and NNLS solver status handling out of the active
   runtime unless that backend is explicitly restored.
3. Fix `findtubeorbitwidth` uninitialized-array risk.
4. Keep active shared-library build coverage for `orblib_fortran/`.
5. Keep GALAHAD dependency paths archived unless a controlled restore is needed.
6. Maintain the small opt-in Fortran/Python LOSVD regression fixture.
7. Convert fixed-size arrays and fragile parsing helpers after the failure semantics are reliable.

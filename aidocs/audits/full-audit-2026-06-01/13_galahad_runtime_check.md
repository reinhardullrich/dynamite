# 13 GALAHAD Runtime Check

Date: 2026-06-01

Current-status update, 2026-06-02: this chapter has been adapted for the
`fortran-cleanup` branch. GALAHAD/NNLS solver code is now archived under
`archive/legacy_nnls_fortran/`, and `LegacyWeightSolver` is rejected by current
configuration/model execution. Treat this chapter as archived-path evidence and
parity/reference context, not an active runtime requirement.

Scope: local GALAHAD 2.3 installation, full archived legacy Fortran build,
linked solver executable checks, and direct GALAHAD/QPB runtime probes.

This section corrects the earlier audit gap: the first full-audit pass covered
static Fortran review and `make nogal`, but it had not proven the GALAHAD-linked
solver path.

## Local Setup Used

No global packages, `sudo`, `apt`, or global compiler/library installs were
used.

The repository already contains local legacy dependency trees:

- `archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/`
- `archive/legacy_nnls_fortran/legacy_fortran/cuter/`
- `archive/legacy_nnls_fortran/legacy_fortran/hsl/`

GALAHAD was installed locally by running:

```bash
cd archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3
./install_galahad
```

Installer choices used:

- PC
- Linux
- GNU gfortran
- QP packages and interfaces to CUTEr
- local CUTEr path:
  `/home/reinhard/projects/thomas/dynamite/archive/legacy_nnls_fortran/legacy_fortran/cuter`
- double precision only

The installer completed with:

```text
GALAHAD: QP routines (double precision version) for CUTEr compiled successfully
```

## Build Result

Initial full DYNAMITE build command:

```bash
cd archive/legacy_nnls_fortran/legacy_fortran
make GALAHADDIR=/home/reinhard/projects/thomas/dynamite/archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3 GALAHADTYPE=pc.lnx.gfo/double all
```

The first attempt failed because the generated GALAHAD static archives were
missing objects required by the final DYNAMITE link:

- `libgalahad.a` lacked `gltr.o`.
- `libgalahad_hsl.a` lacked `hsl_ma57d.o`.

The modules existed, and the installer had printed compile success, but the
archive members were absent. Symbol checks showed unresolved references such
as:

- `__galahad_gltr_double_MOD_gltr_*`
- `__hsl_ma57_double_MOD_ma57_*`

Local generated-artifact repair:

```bash
sed -f archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/seds/double.sed \
  archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/src/gltr/gltr.f90 \
  > /tmp/dynamite-galahad-probe/gltr.f90

gfortran -o /tmp/dynamite-galahad-probe/gltr.o \
  -c -fno-second-underscore -O \
  -I/home/reinhard/projects/thomas/dynamite/archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/modules/pc.lnx.gfo/double \
  /tmp/dynamite-galahad-probe/gltr.f90

gfortran -o /tmp/dynamite-galahad-probe/hsl_ma57d.o \
  -c -fno-second-underscore -O \
  -I/home/reinhard/projects/thomas/dynamite/archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/modules/pc.lnx.gfo/double \
  /home/reinhard/projects/thomas/dynamite/archive/legacy_nnls_fortran/legacy_fortran/hsl/ma57v4/hsl_ma57d.f90

ar -rc archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/objects/pc.lnx.gfo/double/libgalahad.a \
  /tmp/dynamite-galahad-probe/gltr.o
ar -rc archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/objects/pc.lnx.gfo/double/libgalahad_hsl.a \
  /tmp/dynamite-galahad-probe/hsl_ma57d.o
ranlib archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/objects/pc.lnx.gfo/double/libgalahad.a
ranlib archive/legacy_nnls_fortran/legacy_fortran/galahad-2.3/objects/pc.lnx.gfo/double/libgalahad_hsl.a
```

After this local archive repair, the full build succeeded.

Original generated executables before cleanup. These are no longer active
runtime artifacts:

- `archive/legacy_nnls_fortran/legacy_fortran/triaxmass`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxmass_bar`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxmassbin`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxmassbin_bar`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_CRcut`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_noCRcut`
- `archive/legacy_nnls_fortran/legacy_fortran/triaxnnls_bar`

Link/load checks:

- `ldd triaxnnls_CRcut triaxnnls_noCRcut triaxnnls_bar` showed no missing
  dynamic libraries.
- `nm -u triaxnnls_CRcut triaxnnls_noCRcut triaxnnls_bar | rg
  'galahad|hsl|ma57|gltr|qpb'` produced no unresolved GALAHAD/HSL symbol
  matches.
- EOF smoke tests reached DYNAMITE input parsing for all three `triaxnnls_*`
  binaries.

## Runtime Checks

A real DYNAMITE legacy model run was executed in `/tmp/dynamite-galahad-run`
using copied `archive/dev_tests/reimplement_nnls_config1.yaml` and
`archive/dev_tests/NGC6278_input/`, with local edits in `/tmp` only:

- `ncpus: 1`
- `n_max_mods : 1`

The legacy grid still produced 5 models. All 5 completed with
`LegacyWeightSolver`, `nnls_solver: 1`, and shell exit code `0`. This tested the
compiled legacy binary and model pipeline, but it did not exercise GALAHAD/QPB
because solver mode `1` is the classic NNLS mode.

To hit the actual GALAHAD path, a generated `nn.in` was copied to separate
temporary output prefixes and the solver choice was changed from `1` to `5`:

- `ml05.00_galahad/nn.in` for `triaxnnls_noCRcut`
- `ml05.00_galahad_crcut/nn.in` for `triaxnnls_CRcut`

The direct solver-5 commands both exited with shell status `0`, but the logs
showed that GALAHAD/QPB returned non-success:

```text
QPB_solve exit status =     -5
```

The logs also contained:

```text
the problem appears to be infeasible
Error return     -5 from      LSQP_solve
```

Despite this, both runs continued into:

```text
resolving done
finished finding orbweight
* Solving done
Making predictions
writing kinem.out
```

and wrote output files such as `nn_kinem.out`, `nn_nnls.out`, `nn_orb.out`,
and `nn_con.out`.

## Conclusions

- Full GALAHAD-linked compilation is locally possible in this checkout.
- The current local GALAHAD install path is not a clean one-command build under
  GNU Fortran 13.3.0 because two required objects had to be re-added to
  generated static archives.
- The GALAHAD/QPB runtime path was reached in both noCRcut and CRcut binaries.
- The tested GALAHAD/QPB solve did not converge successfully for the generated
  model input; it returned status `-5`.
- The Fortran process still exited `0` and wrote downstream output files after
  GALAHAD reported failure.

This confirms the high-priority solver-status audit finding: Python must not
trust shell exit code or output-file presence alone for GALAHAD-backed legacy
weight solves. It needs to parse or receive explicit solver status and reject
non-success statuses unless a documented policy says otherwise.

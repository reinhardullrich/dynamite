# 06 Orbit Library Boundary

Date started: 2026-06-01

Current-status update, 2026-06-02: this chapter has been adapted for the
`fortran-cleanup` branch. Active orbit-library generation now delegates to
`dynamite/orblib_api.py` and calls
`orblib_fortran/build/lib/liborblib_fortran.so` through `ctypes`. Python passes
the non-bar inputs directly and no longer writes Fortran `infil/` inputs or
launches orbit executables for normal generation. Binary `datfil/` outputs
remain active because the existing readers and weight solvers consume them.

## Scope

This audit section covers:

- `dynamite/orblib.py`
- the direct shared-library API facade in `dynamite/orblib_api.py`
- active direct-memory Fortran inputs
- orbit-library status files under `datfil/`
- compressed Fortran output files
- orbit-library readback into Python histograms and intrinsic masses

## Evidence Reviewed

- `dynamite/orblib.py`
- related model-state calls in `dynamite/model.py`
- related configuration reconciliation in `dynamite/config_reader.py`

## Findings

### OB-001

Severity: High

Area: External process failure detection

Files:

- `dynamite/orblib.py`

Summary:

Orbit-start and orbit-library subprocess wrappers decide success primarily from
whether captured stdout is empty, not from the subprocess return code. A command
or shell script can return non-zero with no stdout and still be logged as
successful.

Evidence:

Initial-condition execution:

```text
orblib.py:457-465
p = subprocess.run(cmd,
                   stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT,
                   shell=True)
...
if not p.stdout.decode("UTF-8"):
    self.logger.info(f'...done - orbitstart{bar} exit code '
                     f'{p.returncode}. {log_file}')
```

Sequential orbit-library execution:

```text
orblib.py:527-541
p = subprocess.run('bash '+cmdstr_tube,
                   stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT,
                   shell=True)
...
if not p.stdout.decode("UTF-8"):
    self.logger.info(f'...done - {cmdstr_tube} exit code '
                     f'{p.returncode}. {log_files}')
```

Parallel orbit-library execution:

```text
orblib.py:488-503
p = subprocess.run('bash '+cmdstr,
                   stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT,
                   shell=True)
...
if not p.stdout.decode("UTF-8"):
    self.logger.info(f'...done - {cmdstr} exit code '
                     f'{p.returncode}. {log_files}')
```

Impact:

Failed Fortran runs can be treated as successful if they do not emit stdout.
This can leave misleading status flags and push the failure downstream into
weight solving or binary file reading, where the error is harder to diagnose.

Recommendation:

Use `subprocess.run(..., check=True)` or explicitly require
`p.returncode == 0`. Log stdout/stderr as diagnostic context, but never use
empty stdout as the success condition.

Verification:

Replace a generated command with `exit 2` and no output. The Python wrapper
should raise immediately and not mark the orbit library done.

### OB-002

Severity: High

Area: Generated shell scripts mark done unconditionally

Files:

- `dynamite/orblib.py`

Summary:

Generated shell scripts do not use `set -e` and touch `tube_done`/`box_done`
after running the Fortran executable and optional compression commands. The done
files are not conditional on all required output files being present and
successfully compressed.

Evidence:

Parallel script:

```text
orblib.py:601-622
txt_file.write('# now run tube and box orbits in parallel\n')
...
txt_file.write(f'{self.legacy_directory}/{orb_prgrm} < infil/orblib.in '
                '>> datfil/orblib.log\n')
...
txt_file.write('touch datfil/tube_done) &\n')
```

```text
orblib.py:627-634
txt_file.write(f'{self.legacy_directory}/{orb_prgrm} '
               '< infil/orblibbox.in >> datfil/orblibbox.log\n')
...
txt_file.write('touch datfil/box_done) &\n')
```

Sequential script:

```text
orblib.py:671-688
txt_file.write(f'{self.legacy_directory}/{orb_prgrm} < infil/orblib.in '
               '>> datfil/orblib.log\n')
...
txt_file.write('touch datfil/tube_done\n')
```

```text
orblib.py:708-717
txt_file.write(f'{self.legacy_directory}/{orb_prgrm} '
               '< infil/orblibbox.in >> datfil/orblibbox.log\n')
...
txt_file.write('touch datfil/box_done\n')
```

`get_orblib()` trusts those flags:

```text
orblib.py:148-151
tube_done = os.path.isfile(self.mod_dir + 'datfil/tube_done')
box_done = os.path.isfile(self.mod_dir + 'datfil/box_done')
if tube_done and box_done:
    pathlib.Path(self.mod_dir + 'datfil/tube_box_done').touch()
```

Impact:

An orbit-library run can be marked complete even when the actual `.dat.bz2`
files are missing, stale, empty, or partially compressed. This is a major
resume/reproducibility risk because later code treats `tube_box_done` as an
orbit-library completion signal.

Recommendation:

In generated scripts:

- start with `set -euo pipefail`
- use temporary output names
- after each executable, verify all expected files exist and are non-empty
- compress through staging files and atomic `mv`
- touch done files only after all checks pass

In Python:

- after script completion, verify the expected compressed files before touching
  `tube_box_done`

Verification:

Simulate missing `orblib_losvd_hist.dat` after a Fortran run and assert no done
file is created.

### OB-003

Severity: Medium

Area: Readback decompression ignores return codes

Files:

- `dynamite/orblib.py`

Summary:

Orbit-library readback uses `bunzip2 -c ... > tmpfile` through
`subprocess.run(..., shell=True)` without checking the return code before
opening the temporary file as a Fortran binary.

Evidence:

```text
orblib.py:832-836
subprocess.run(f'bunzip2 -c {orblib_file} > {tmpfname}', shell=True)
# read the fortran file
orblib_in = FortranFile(tmpfname, 'r')
```

```text
orblib.py:891-896
orblib_file = f'datfil/{fileroot}_losvd_hist.dat.bz2'
tmpfname = f'datfil/{fileroot}_losvd_hist_{ml}.dat'
subprocess.run(f'bunzip2 -c {orblib_file} > {tmpfname}',
               shell=True)
# read the fortran file
orblib_in = FortranFile(tmpfname, 'r')
```

```text
orblib.py:994-997
tmpfname = f'datfil/{fileroot}_pops_{ml}.dat'
subprocess.run(f'bunzip2 -c {pops_file} > {tmpfname}', shell=True)
# read the fortran file
orblib_in = FortranFile(tmpfname, 'r')
```

Impact:

Missing or corrupt compressed files can produce empty/partial temporary files.
The resulting error is then a low-level Fortran read failure instead of a clear
decompression or file-integrity error.

Recommendation:

Use Python's `bz2` library or run `bunzip2` with `check=True`. Verify the
temporary file exists and is non-empty before opening it. Prefer avoiding shell
redirection entirely.

Verification:

Try to read a deliberately corrupted `.bz2` file and assert the error names the
corrupt compressed file.

### OB-004

Severity: Medium

Area: Working-directory restoration and temporary-file cleanup

Files:

- `dynamite/orblib.py`

Summary:

Several methods change the process working directory and then perform multiple
file operations without `try/finally`. If binary readback fails, the current
working directory and temporary files may be left behind.

Evidence:

```text
orblib.py:808-836
cur_dir = os.getcwd()
os.chdir(self.mod_dir)
...
subprocess.run(f'bunzip2 -c {orblib_file} > {tmpfname}', shell=True)
orblib_in = FortranFile(tmpfname, 'r')
```

Cleanup happens on some normal/error paths:

```text
orblib.py:872-875
orblib_in.close()
os.remove(tmpfname)
os.chdir(cur_dir)
```

but many reads occur between `chdir()` and cleanup:

```text
orblib.py:839-858
norb_read, _, _, _, ndith = orblib_in.read_ints(np.int32)
...
quad_lph = orblib_in.read_reals(float)
```

Impact:

An exception during readback can leave the Python process in a model directory.
Subsequent relative file operations may then run in the wrong location. Stale
temporary `.dat` files can also consume disk and confuse later manual
inspection.

Recommendation:

Avoid `os.chdir()` by using absolute paths where possible. Where chdir remains,
wrap it with `try/finally` that restores `cur_dir`, closes open files, and
removes temporary files.

Verification:

Force a read failure after `os.chdir(self.mod_dir)` and assert that
`os.getcwd()` is restored and temporary files are removed.

### OB-005

Severity: Medium

Area: Compatibility checks depend on `assert`

Files:

- `dynamite/orblib.py`

Summary:

Important orbit-library compatibility checks use `assert`, which disappears
under optimized Python.

Evidence:

Velocity symmetry before tube-orbit duplication:

```text
orblib.py:1030-1033
error_msg = 'velocity array must be symmetric'
assert np.allclose(orblib.xedg, -orblib.xedg[::-1]), error_msg
```

Tube/box compatibility before combining:

```text
orblib.py:1074-1082
assert n_vel_bins1==n_vel_bins2, error_msg
...
assert np.array_equal(orblib1.x, orblib2.x), error_msg
...
assert n_spatial_bins1==n_spatial_bins2, error_msg
```

Impact:

With `python -O`, incompatible orbit libraries can be combined without the
intended guard. That can produce wrong array alignment or later shape errors.

Recommendation:

Replace `assert` with explicit `if` checks that raise `ValueError`.

Verification:

Run the compatibility tests with `PYTHONOPTIMIZE=1`.

### OB-006

Severity: Medium

Area: Tube/box list length mismatch

Files:

- `dynamite/orblib.py`

Summary:

Tube and box orbit-library lists are combined with `zip()`, which silently
truncates if one side has more entries than the other. The per-histogram shape
checks do not catch a list-length mismatch.

Evidence:

```text
orblib.py:1153-1156
# combine orblibs
orblib = []
for (t0, b0) in zip(tube_orblib, box_orblib):
    orblib.append(self.combine_orblibs(t0, b0))
```

Impact:

If tube and box outputs contain a different number of kinematic/population
histogram sets, the extra data is dropped silently. This could lead to missing
constraints in weight solving.

Recommendation:

Check `len(tube_orblib) == len(box_orblib)` before zipping and include the
model directory and file roots in the error message.

Verification:

Construct fake tube/box histogram lists with different lengths and assert that
read/combination fails explicitly.

### OB-007

Severity: Low

Area: Parallel compression atomicity

Files:

- `dynamite/orblib.py`

Summary:

The sequential script writes compressed output through staging files and then
renames them. The parallel script uses `bzip2 -k` directly for the same outputs.

Evidence:

Sequential:

```text
orblib.py:684-686
test -e {f_name} && bzip2 -kc {f_name} > {f_name}.staging.bz2
&& mv {f_name}.staging.bz2 {f_name}.bz2
```

Parallel:

```text
orblib.py:619-620
test -e {f_name} && rm -f {f_name}.bz2 && bzip2 -k {f_name}
```

Impact:

An interrupted parallel compression can leave partial final `.bz2` files more
easily than the sequential staging pattern.

Recommendation:

Use the same staging-and-rename pattern in both scripts.

Verification:

Interrupt compression in a controlled test and assert final `.bz2` files are
not left partially written.

## Positive Observations

- The active Python layer now passes Fortran inputs through the direct
  shared-library API and keeps binary outputs under `datfil/`.
- New-format orbit-library files split qgrid, LOSVD histograms, and population
  outputs, which makes presence checks more specific than the legacy monolith.
- `AllModels.update_orblib_flags()` checks for required compressed outputs and
  can remove stale done indicators during reconciliation.
- Temporary decompressed file names include `ml`, reducing some cross-process
  collisions during weight-solving reads.

## Open Questions

- Should shared-library worker failures expose more structured Fortran error
  metadata than process failure alone?
- Should `tube_box_done` be deprecated in favor of checking the actual required
  `.bz2` file set every time?
- Are parallel orbit-library runs actively used, and do they need stronger
  independent logging for tube and box failures?

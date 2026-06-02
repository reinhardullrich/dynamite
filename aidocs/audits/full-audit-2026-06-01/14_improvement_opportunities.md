# 14 Improvement Opportunities

Date: 2026-06-01

Scope: non-bug-fix improvements that could make DYNAMITE faster, smoother,
cleaner, easier to develop, and easier to run repeatedly.

Current-status update, 2026-06-02: this chapter has been adapted for the
`fortran-cleanup` branch. The active Fortran build is now shared-library-only,
`LegacyWeightSolver` is rejected by current runtime configuration, and old
GALAHAD/NNLS sources are archived. Recommendations that originally proposed a
future transition now describe the current local state where applicable.

This chapter is intentionally separate from the bug/risk audit. It does not
recommend changing scientific behavior first. It recommends improving the
execution model, data flow, APIs, and developer ergonomics around the existing
behavior.

## Guiding Principle

Do not optimize by rewriting the scientific core blindly. First make the
runtime observable:

- measure import time;
- measure wall time per model stage;
- measure bytes read/written per model;
- measure peak memory during orbit-library reading and NNLS matrix assembly;
- record solver backend, compiler flags, CPU count, and cache hit/miss state.

After that, make small improvements at the boundaries where the code already
spends time: imports, disk I/O, table scans, decompression, array assembly, and
process orchestration.

## Runtime Reality Check

Startup is measurable, but it is not the main cost of a full DYNAMITE model run.

Local import timing in this audit environment:

- `import dynamite`: about 3.6 seconds median.
- querying only installed package metadata for the DYNAMITE version: about
  0.09 seconds median.
- `import numpy`: about 0.19 seconds median.

So eager imports are real overhead for command-line tools, test collection,
notebooks, metadata checks, and repeated short-lived helper processes.

For full model runs, that startup cost is small. In the temporary original
GALAHAD/legacy test run, 5 models took about 386 seconds total. New orbit
libraries spent roughly a minute in initial conditions and about 50 seconds in
tube/box orbit integration. The classic legacy weight solves took only a few
seconds each. That means full orbit-library generation is dominated by Fortran
backend work and disk I/O around it, not Python import time.

The practical conclusion:

- lazy imports are a useful quick win for developer experience and short tools;
- they are not the first lever for accelerating production orbit-library runs;
- the highest runtime payoff is likely in cache reuse, data formats,
  decompression/I/O, solver matrix preparation, and avoiding unnecessary
  repeated orbit-library work.

## Highest Runtime-Payoff Improvements

### IM-001 - Replace ASCII/ECSV hot-path storage with binary sidecars

Potential payoff: faster repeated runs, lower disk I/O, lower parsing overhead,
smaller output folders.

Evidence:

- `dynamite/model.py:119` reads `all_models.ecsv` with Astropy ASCII.
- `dynamite/model.py:682` writes `all_models.ecsv` on every save.
- `dynamite/weight_solvers.py:864-866` writes weights as ASCII ECSV.
- `dynamite/mges.py:157`, `432-435`, and `251-252` read/write mass arrays via
  ASCII tables.
- `dynamite/analysis.py` writes many derived arrays as ASCII ECSV.

Improvement:

Keep ECSV as a human-readable export format, but use binary sidecars for hot
runtime state:

- `.npz` or HDF5 for dense arrays such as masses, weights, LOSVD-derived
  matrices, and projected/intrinsic moments;
- ECSV only for small metadata and final inspection tables;
- a tiny manifest that records schema version, source config hash, shapes, and
  physical units.

This does not require changing scientific outputs. It changes the storage layer
so repeated reads avoid expensive text parsing.

Implementation size: medium.

Risk: medium because cache invalidation and schema versioning must be explicit.

### IM-002 - Cache prepared NNLS matrices by orbit-library plus settings key

Potential payoff: much faster re-solving when only the solver backend,
regularisation, or mass-to-light value changes.

Evidence:

- `dynamite/weight_solvers.py:813-816` reads LOSVD histograms and constructs a
  full matrix for every Python NNLS solve.
- `dynamite/weight_solvers.py:670-729` constructs `con`, `econ`, and `orbmat`
  from mass constraints, projected masses, LOSVD transforms, and kinematic
  constraints.
- The same orbit library can be reused by several `ml` variants in
  `model_iterator.py:330-343`.

Improvement:

Introduce a cache layer for the standardized matrix components:

- orbit-library density block;
- projected-mass block;
- per-kinematic-set transformed observable block;
- final error-scaled matrix and RHS if settings match exactly.

Cache key should include:

- orbit-library directory;
- kinematic input file hashes;
- `number_GH`, `GH_sys_err`, projected/intrinsic mass error settings;
- `CRcut` setting;
- velocity scaling factor / `ml`;
- code/schema version.

Implementation size: medium.

Risk: medium. Correct cache invalidation matters more than raw speed.

### IM-003 - Avoid repeated full table scans for model and orbit-library lookup

Potential payoff: smoother scaling when model grids grow.

Evidence:

- `dynamite/model.py:499-501` scans all rows to find a parset.
- `dynamite/model.py:581-584` scans all rows to find a model row.
- `dynamite/model.py:626-628` scans earlier rows to find the original orbit
  library.
- `dynamite/model_iterator.py:409-412` scans previous rows to decide whether an
  orbit library is new.
- `dynamite/model_iterator.py:464-468` scans earlier rows again to assign
  existing orbit-library directories.

Improvement:

Build stable model keys once per table update:

- `model_key`: all model parameters serialized using configured parameter
  formatting;
- `orblib_key`: all orbit-library-defining parameters, excluding `ml` where
  appropriate;
- dictionaries from key to row index and key to directory.

Then lookups become O(1), and the key becomes visible metadata for debugging and
cache validation.

Implementation size: medium.

Risk: low/medium. The main design choice is exact key formatting.

### IM-004 - Improve orbit-library reading without temporary decompression files

Potential payoff: lower disk I/O and less workspace churn.

Evidence:

- `dynamite/orblib.py:832-836` decompresses a `.bz2` orbit-library file into a
  temporary `.dat` file before reading it.
- `dynamite/orblib.py:891-896` repeats the same pattern for LOSVD histogram
  files.
- `dynamite/orblib.py:993-997` repeats it for population files.

Improvement:

Evaluate reading compressed files through a streaming layer or a managed
temporary-file abstraction that:

- checks return codes;
- uses unique temp names;
- deletes files reliably;
- can skip repeated decompression when the compressed input hash is unchanged.

If `scipy.io.FortranFile` requires seekable files, use a controlled local cache
directory instead of writing temp files beside production outputs.

Implementation size: medium.

Risk: medium because Fortran record readers may need seekable input.

## Quick Developer-Experience Improvements

### IM-005 - Lazy package imports

Potential payoff: faster startup, smoother CLI/notebook use, less import-time
dependency friction.

Evidence:

- `dynamite/__init__.py:1` imports nearly every package module eagerly.
- Importing DYNAMITE currently pulls in plotting/coloring dependencies even for
  workflows that only need configuration or model bookkeeping.

Improvement:

Keep `__version__` and a minimal public surface in `dynamite/__init__.py`.
Move heavy imports behind explicit imports or lazy module loading.

Example target behavior:

```python
import dynamite
dynamite.__version__

from dynamite.config_reader import Configuration
```

instead of making `import dynamite` import analysis, coloring, plotting, PyMC,
Matplotlib, VorBin, and all runtime modules.

Implementation size: small.

Risk: low if public imports are kept backward compatible for one release cycle.

### IM-006 - Split configuration parsing from output-tree mutation

Potential payoff: smoother tooling, faster dry runs, easier testing, safer
interactive use.

Evidence:

- `dynamite/config_reader.py:247-251` can delete and recreate output directories
  during configuration construction.
- `dynamite/config_reader.py:564-576` constructs `AllModels`, scans existing
  directories, updates flags, and updates the model table during construction.
- `dynamite/config_reader.py:254-542` mixes YAML parsing, object construction,
  validation, defaulting, path handling, and runtime setup in one long method.

Improvement:

Introduce explicit phases:

1. Parse config YAML into a validated, immutable config object.
2. Build system/settings objects.
3. Prepare or inspect output state.
4. Run model iteration.

This would make it possible to run fast read-only commands like:

```python
Configuration.parse("config.yaml")
Configuration.validate("config.yaml")
Configuration.plan("config.yaml")
```

without touching output directories.

Implementation size: large but can be staged.

Risk: medium. Backward-compatible constructors can delegate to the new phases.

## Performance-Focused Improvements

### IM-007 - Preallocate NNLS arrays instead of repeated concatenation/stacking

Potential payoff: lower memory churn during Python NNLS matrix assembly.

Evidence:

- `dynamite/weight_solvers.py:721-725` repeatedly concatenates `con`, `econ`,
  and vertically stacks `orbmat` inside the kinematic-set loop.

Improvement:

Compute the total number of constraints first, allocate final arrays once, and
fill slices. This also makes expected shapes easier to validate and log.

Implementation size: small/medium.

Risk: low if covered by shape-focused regression tests.

### IM-008 - Make MGE integrations more cacheable and chunkable

Potential payoff: faster repeated projected/intrinsic mass calculations and
better CPU utilization.

Evidence:

- `dynamite/mges.py:200-236` performs nested integration over grid cells, MGE
  components, and PSF components.
- `dynamite/mges.py:421-540` defines nested functions for intrinsic mass and
  potential/acceleration integrations.
- The current projected-mass cache is a single output file at
  `dynamite/mges.py:154-160`.

Improvement:

Separate integration plan creation from execution:

- precompute MGE/PSF constants once;
- build independent work chunks;
- cache results by input file hash, MGE parameters, aperture/bin file hash,
  distance, and quadrature settings;
- expose a simple progress meter and timing summary.

For speed experiments, benchmark:

- current SciPy `quad`;
- vectorized quadrature where applicable;
- Numba-compiled integrands for pure numerical inner loops;
- process chunk sizes tuned to reduce IPC overhead.

Implementation size: medium/large.

Risk: medium. Numerical equivalence tolerances must be defined before replacing
integrators.

### IM-009 - Introduce stage timing and model run manifests

Potential payoff: easier optimization, easier support, clearer performance
regressions.

Evidence:

- Model iteration has distinct stages in `dynamite/model_iterator.py:344-388`:
  orbit-library generation, weight solving, external chi-square, and save.
- Current logs record stage messages but not a consistent machine-readable
  timing manifest.

Improvement:

Write a small `run_manifest.json` per model or per iteration with:

- command versions and executable hashes;
- CPU counts;
- stage start/end/duration;
- input/output file sizes;
- cache hits/misses;
- solver backend and status;
- peak memory if available.

Implementation size: small/medium.

Risk: low.

## Smoothness and Developer-Ergonomics Improvements

### IM-010 - Replace generated shell scripts with a small command-runner layer

Potential payoff: shorter code, cleaner logs, easier local/cluster execution.

Evidence:

- `dynamite/orblib.py:588-638`, `652-688`, and `693-717` write shell scripts
  for orbit-library execution.
- `dynamite/weight_solvers.py:397-427` writes shell scripts for legacy weight
  solving.

Improvement:

Keep script generation for reproducibility if desired, but generate it from a
structured command model:

```python
CommandSpec(
    argv=[legacy_dir / "triaxnnls_noCRcut"],
    stdin=nn_input,
    stdout=nn_log,
    required_outputs=[...],
    status_parser=parse_nnls_status,
)
```

Then one executor can:

- run locally with `subprocess`;
- write an equivalent shell script for cluster submission;
- record the command manifest;
- validate outputs consistently.

Implementation size: medium.

Risk: low/medium. It can be introduced behind current generated scripts.

### IM-011 - Add a small public API layer for common workflows

Potential payoff: shorter user scripts and less direct coupling to internal
classes.

Evidence:

- Dev tests and examples instantiate `Configuration`, `ModelIterator`, plotting,
  and analysis classes directly.
- Configuration construction currently has side effects, so users have to know
  which calls mutate output state.

Improvement:

Provide top-level workflow functions with explicit names:

```python
dynamite.validate_config(path)
dynamite.plan_models(path)
dynamite.run_models(path, *, reset=False, ncpus=None)
dynamite.resume_models(path)
dynamite.summarize_run(path)
```

These can preserve the current internals while making scripts shorter and less
fragile.

Implementation size: medium.

Risk: low if implemented as wrappers first.

### IM-012 - Move from ad hoc dict settings toward typed settings objects

Potential payoff: shorter validation code, better editor support, fewer runtime
key lookups.

Evidence:

- `dynamite/config_reader.py:42-63` stores settings in broad dict attributes.
- Many modules access nested dict keys directly, for example
  `weight_solvers.py`, `model_iterator.py`, and `mges.py`.

Improvement:

Introduce typed settings dataclasses or Pydantic-style models at the boundary,
then pass typed objects internally. This can start with read-only wrappers
around existing dicts.

Target:

```python
settings.orblib.nE
settings.weight_solver.nnls_solver
settings.multiprocessing.ncpus_weights
```

instead of repeated string-key access.

Implementation size: large if done globally, small if introduced incrementally.

Risk: medium because config compatibility matters.

### IM-013 - Reduce large method size by extracting stage-specific helpers

Potential payoff: shorter, testable units and easier future changes.

Evidence:

- `dynamite/config_reader.py:254-542` contains most config object assembly in a
  single loop.
- `dynamite/weight_solvers.py:656-729` mixes mass constraints, projected
  constraints, kinematic transformation, CRcut, and final scaling in one method.
- `dynamite/orblib.py:762-1009` handles legacy/new file detection,
  decompression, Fortran binary reading, LOSVD construction, and population
  reading in one method.

Improvement:

Extract helpers by domain stage:

- config schema validation;
- component construction;
- kinematic construction;
- MGE construction;
- orbit-library file opening;
- qgrid reading;
- LOSVD reading;
- matrix block assembly.

This is not just style. Smaller stage functions make profiling, caching, and
unit testing much easier.

Implementation size: medium.

Risk: low if extracted without behavior changes.

## Fortran and Native-Code Improvements

### IM-014 - Add named build profiles

Potential payoff: smoother development, reproducible comparisons, easier
performance testing.

Evidence:

- `orblib_fortran/Makefile` uses a speed-oriented profile with `-ffast-math`,
  `-march=native`, and other optimization flags.
- The archived GALAHAD build required manual knowledge of `GALAHADDIR` and
  `GALAHADTYPE`.

Improvement:

Add documented build profiles:

- `fast-local`: current speed-oriented build;
- `portable`: no `-march=native`;
- `debug`: bounds checks, backtraces, no fast math;
- `shared`: current active shared-library build;
- `clean-generated`: remove local objects and shared-library artifacts safely.

Implementation size: medium.

Risk: low if existing default target remains unchanged initially.

### IM-015 - Define a modern optional solver path as the preferred future path

Potential payoff: simpler installs and less dependence on very old GALAHAD/HSL
tooling. The payoff is not mainly faster fresh orbit-library generation; that
is still dominated by the Fortran orbit backend. The payoff is cleaner
installation, better status handling, easier caching, and faster repeated
weight-solving workflows once orbit libraries already exist.

Evidence:

- `dynamite/weight_solvers.py` still contains `LegacyWeightSolver` source for
  historical reference, but current configuration/model execution rejects it
  because its Fortran solver binaries are archived.
- `dynamite/weight_solvers.py:595-613` defines the Python `NNLS` solver with
  `nnls_solver in ['scipy', 'cvxopt']`.
- `dynamite/weight_solvers.py:656-729` already constructs the explicit Python
  matrix/RHS representation of the weight-solving problem.
- `docs/more_info/changelog.rst` says `LegacyWeightSolver` is deprecated and
  will be removed along with GALAHAD in a future DYNAMITE version.
- `docs/getting_started/configuration.rst` documents `type: "NNLS"` with
  `nnls_solver: "scipy"` or `"cvxopt"`, and states that `BayesLOSVD` requires
  `type: "NNLS"`.
- The local GALAHAD audit showed the full legacy build is possible but fragile,
  and that solver status can be masked after GALAHAD/QPB failure.

Improvement:

Treat the Python `NNLS` path as the modern default for new development, and
keep legacy GALAHAD/Fortran archived unless a controlled reproduction task
explicitly restores it.

This should not mean "delete GALAHAD". It should mean:

- new features target the Python `NNLS` interface first;
- archived legacy Fortran remains available as source material for reproducing
  older results;
- GALAHAD remains useful only as an archived independent reference unless
  restored behind an explicit backend;
- the codebase stops assuming that every serious run must have GALAHAD/HSL
  compiled locally.

Recommended architecture:

```python
SolverProblem(
    A=A,
    b=b,
    bounds=(0, np.inf),
    row_blocks={
        "total_mass": ...,
        "intrinsic_mass": ...,
        "projected_mass": ...,
        "kinematics": ...,
    },
    metadata={
        "orblib_key": ...,
        "ml": ...,
        "CRcut": ...,
        "regularisation": ...,
        "number_GH": ...,
    },
)

SolverResult(
    weights=...,
    success=True,
    status=...,
    message=...,
    backend="scipy.nnls",
    residual_norm=...,
    iterations=...,
    elapsed_seconds=...,
    raw_backend_info=...,
)
```

Every backend should return the same result object. Python code should then
validate `success`, finite/non-negative weights, finite chi-square values, and
expected dimensions before saving model outputs.

Candidate backend tiers:

1. `scipy.nnls`
   - closest to current Python default;
   - simple non-negative least squares interface;
   - good baseline for dense problems;
   - limited status metadata compared with richer bounded solvers.

2. `scipy.lsq_linear(bounds=(0, np.inf))`
   - solves bounded linear least-squares problems;
   - can use dense arrays, sparse arrays, or `LinearOperator`;
   - returns a richer result object than `nnls`;
   - useful if future constraints become lower/upper bounded rather than only
     non-negative.

3. `cvxopt`
   - useful independent QP backend and cross-check;
   - can express the same non-negative least-squares problem as a quadratic
     program;
   - may be less attractive for very large dense normal-equation matrices
     because the current code forms `P = A.T @ A`.

4. sparse/iterative experimental path
   - only worth prioritizing if measured matrix density is low enough;
   - the legacy noCRcut log for one model reported about 68 percent non-zero
     ORBMAT entries, which is not obviously sparse enough;
   - still worth designing the interface so sparse matrices or `LinearOperator`
     backends remain possible.

5. archived legacy Fortran/GALAHAD reference path
   - keep as archived source material for parity checks and old-result
     reproduction;
   - wrap it behind the same `SolverResult` concept;
   - parse Fortran/GALAHAD status explicitly instead of treating output files as
     success.

The highest-value optimization is probably not "choose a different solver" by
itself. It is "make the weight-solving problem an explicit cached object".
Once `A`, `b`, row metadata, and scaling metadata are stable, the project can:

- matrix caching;
- compare backends on the exact same problem;
- avoid rebuilding matrix blocks for repeated `ml` or solver-backend runs;
- store per-block chi-square contributions consistently;
- add sparse or bounded backends without rewriting orbit-library logic;
- run a parity harness automatically.

Required parity checks before changing defaults:

1. Archived classic NNLS parity
   - Restore/run `LegacyWeightSolver` with `nnls_solver: 1` only in a controlled
     archived-backend parity harness.
   - Run Python `NNLS` with `nnls_solver: "scipy"` on the same generated orbit
     library.
   - Compare weights, total chi-square, kinematic chi-square, map chi-square,
     and key output files.

2. CRcut parity
   - Use configs with `CRcut: True`.
   - Confirm Python `apply_CR_cut()` reproduces the intended Fortran behavior.
   - Compare which orbits are cut and how this affects h1/h2 or
     velocity/sigma terms.

3. M/L rescaling parity
   - Reuse one orbit library across multiple `ml` values.
   - Confirm velocity scaling and output directories match the legacy
     expectations.

4. Barred and BayesLOSVD coverage
   - Barred models should be tested separately because orbit ordering and
     kinematic assumptions differ.
   - BayesLOSVD already requires `NNLS`, so it should be part of the modern
     path's required test surface.

5. Solver status parity
   - Backends need a shared success/failure contract.
   - Archived legacy Fortran/GALAHAD should be restored only if non-zero solver
     statuses are exposed and recorded.

Suggested staged plan:

1. Add `SolverProblem` and `SolverResult` internally while preserving current
   public config names.
2. Make SciPy NNLS return a full `SolverResult` and write backend/status
   metadata into the weight file.
3. Add a parity test that runs `reimplement_nnls_config1.yaml` and
   `reimplement_nnls_config2.yaml` in temporary output directories and compares
   results.
4. Cache `SolverProblem` matrix blocks in a binary format keyed by
   orbit-library/settings hashes.
5. Add `scipy.lsq_linear` as an experimental backend behind an explicit config
   value such as `nnls_solver: "scipy_lsq_linear"`.
6. Measure matrix density and memory footprint before adding a sparse path.
7. Keep `type: "NNLS"` as the active path for new configs and keep
   `LegacyWeightSolver` rejected unless a controlled reproduction backend is
   explicitly restored.

What this does not solve:

- It does not speed up fresh Fortran orbit integration.
- It does not remove the possible need for archived legacy source when
  reproducing historical published outputs.
- It does not prove scientific equivalence automatically; the parity harness is
  mandatory.
- It does not make sparse methods valuable unless the actual matrices are
  sparse enough.

Implementation size: medium/large.

Risk: medium. Needs scientific parity checks against legacy outputs, especially
for CRcut, bar workflows, and repeated-M/L orbit-library reuse.

## Suggested Roadmap

### First pass: quick wins

1. Measure one small model run with a timing manifest.
2. Add O(1) model/orbit-library lookup keys next to the existing table.
3. Preallocate NNLS matrix arrays instead of repeated concatenate/vstack.
4. Make `dynamite/__init__.py` lazy or minimal for short tools and tests.
5. Add named local build commands/docs for the active shared library and any
   explicitly restored archived solver build.

### Second pass: runtime throughput

1. Add binary sidecar caches for mass arrays and weights.
2. Cache prepared NNLS matrix blocks by orbit-library/settings key.
3. Replace repeated decompression temp files with managed cache files.
4. Add per-stage timing and cache-hit metrics.

### Third pass: architecture cleanup

1. Split configuration parsing from output-state mutation.
2. Introduce typed settings wrappers.
3. Replace generated shell fragments with structured command specs.
4. Expose a small public workflow API for validate/plan/run/resume/summarize.

## What Not To Do First

- Do not rewrite the Fortran numerical core before there is a benchmark suite.
- Do not restore or replace GALAHAD/HSL blindly without parity tests.
- Do not change file formats without schema versioning and migration/export
  support.
- Do not optimize individual formulas before measuring full workflow time.
- Do not make broad refactors before isolating output-state side effects.

The best first improvements are boundary improvements: better runtime
measurement, less text parsing, less repeated table scanning, clearer command
execution, and faster imports for short-lived tooling.

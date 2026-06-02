# How DYNAMITE Works

Last updated: 2026-06-02

This is an internal AI/agent guide for the local DYNAMITE fork. It is written
to make future work easier without modifying upstream source, upstream docs,
orblib Fortran, or development tests.

## Scope And Boundaries

This document explains the current repository and runtime flow as observed in
the checkout at `/home/reinhard/projects/thomas/dynamite`.

Important boundaries:

- `aidocs/` is local AI/agent documentation.
- `docs/` is upstream DYNAMITE Sphinx documentation and should not receive
  local AI notes.
- `dynamite/` is the upstream Python package.
- `orblib_fortran/` is the active orbit-library Fortran backend.
- `archive/dev_tests/` contains archived upstream development tests, sample
  configs, input data, and notebooks.

Local AI notes still belong in `aidocs/`; user-facing Markdown such as the root
README and `tests/README.md` may be updated when their instructions are stale.

## Repository Identity

This local checkout is a personal fork of upstream DYNAMITE.

- Local path: `/home/reinhard/projects/thomas/dynamite`
- Personal fork remote: `origin -> git@github.com:reinhardullrich/dynamite.git`
- Upstream remote: `upstream -> https://github.com/dynamics-of-stellar-systems/dynamite.git`
- Default branch observed locally: `master`

Use `origin` for personal work. Use `upstream` to fetch or merge changes from
the original project.

The sibling CiFoS work is intentionally outside this repo:

- `/home/reinhard/projects/thomas/cifos`

This fork should stay DYNAMITE-focused.

## Mental Model

DYNAMITE is a scientific modelling package. It does not behave like a small
library where most work happens in one function. A run is an orchestrated,
disk-backed workflow:

1. A YAML config describes a galaxy/system, input files, parameters, solver
   choices, orbit-library settings, and output paths.
2. Python reads the config and builds runtime objects.
3. The code generates model parameter combinations.
4. For each model, it builds or reuses an orbit library.
5. It solves for non-negative orbit weights that reproduce observed data.
6. It writes model status, chi-square values, and output artifacts to disk.
7. It iterates until configured stopping criteria are met.
8. It can produce plots and analysis products from the model outputs.

The short user-facing entry point hides most of this:

```python
import dynamite as dyn

c = dyn.config_reader.Configuration("my_config.yaml")
_ = dyn.model_iterator.ModelIterator(c)
```

The main control path is:

```text
YAML config
  -> Configuration
  -> System + Components + Data + Settings
  -> ParameterSpace
  -> AllModels table
  -> ParameterGenerator
  -> ModelIterator / ModelInnerIterator
  -> Model
  -> LegacyOrbitLibrary
  -> WeightSolver
  -> all_models.ecsv + model directories + plots
```

## Top-Level Layout

```text
dynamite/
  AGENTS.md             Local agent instructions for this fork
  aidocs/               Local AI/agent docs and audit notes
  README.md             Upstream project README
  setup.py              Python packaging metadata
  requirements.txt      Python runtime dependencies
  .github/workflows/    Upstream CI
  dynamite/             Python package
  orblib_fortran/       Active orbit-library Fortran backend
    source/             Human-written Fortran source
      numerics/         Bundled numerical routines
      unused/           Inactive retained Fortran sources
    build/lib/          Ignored generated shared library
  docs/                 Upstream Sphinx docs and tutorial notebooks
  archive/dev_tests/    Archived upstream development tests, configs, sample data
```

The nested `dynamite/dynamite` shape is normal Python packaging layout:

- outer `dynamite/`: repository root
- inner `dynamite/`: importable Python package

Do not flatten this. Flattening would break imports and packaging.

## Packaging And Installation Shape

`setup.py` declares the package name as `dynamite`, requires Python `>=3.10`,
uses `setuptools.find_packages()`, reads dependencies from `requirements.txt`,
and includes the compiled orblib Fortran shared library path as package data.

The current local README describes the active installation sequence:

1. Compile the Fortran shared library in `orblib_fortran/`.
2. Install the Python package from the repository root:

```bash
python -m pip install .
```

Important runtime dependencies include:

- `numpy`
- `scipy`
- `astropy`
- `matplotlib`
- `h5py`
- `PyYAML`
- `lmfit`
- `pymc`
- `numba`
- `sparse`
- `pathos`
- `vorbin`, `plotbin`, `powerbin`, `pafit`

`cvxopt` is optional and only needed when using the `cvxopt` NNLS backend.

The requirements file intentionally avoids SciPy 1.12 through 1.15 because the
NNLS implementation in those releases is documented in the file as slower or
more failure-prone for this project.

## Configuration Is The Real Entry Point

The central object is `dynamite.config_reader.Configuration`.

`Configuration(filename)` does much more than parse YAML. It:

1. Sets up logging if requested.
2. Reads YAML with `UniqueKeyLoader`, which rejects duplicate YAML keys.
3. Creates an empty `physical_system.System`.
4. Creates a `Settings` container.
5. Normalizes input/output path strings.
6. Creates output, model, and plot directories if needed.
7. Instantiates components from `system_components`.
8. Instantiates kinematic data, population data, and MGE data objects.
9. Reads system-level parameters and attributes.
10. Reads orbit-library, parameter-space, legacy, weight-solver, IO, and
    multiprocessing settings.
11. Validates the system and settings.
12. Builds `ParameterSpace`.
13. Builds `AllModels`.
14. Updates status for existing model outputs.
15. Precomputes projected mass constraints for non-legacy weight solving.

The config file is therefore not just input. It is a complete recipe for a
disk-backed modelling campaign.

## Config Sections

Typical config sections are:

- `system_attributes`
- `system_components`
- `system_parameters`
- `orblib_settings`
- `weight_solver_settings`
- `parameter_space_settings`
- `legacy_settings`
- `io_settings`
- `multiprocessing_settings`

### system_attributes

Allowed attributes are currently:

- `distMPc`: distance in megaparsecs.
- `name`: system name.

The code rejects unknown keys in this section.

### system_components

This section declares physical components such as:

- `Plummer`: normally used for the central black hole / compact component.
- `TriaxialVisibleComponent`: stellar component with MGE and kinematics.
- `BarDiskComponent`: barred/disk visible component variant.
- `NFW`, `NFW_m200_c`, `Hernquist`, `TriaxialCoredLogPotential`,
  `GeneralisedNFW`: dark components.
- `Chi2Ext`: optional external chi-square contribution.

For ordinary components, the config value `type` is used as a class name under
`dynamite.physical_system`.

Visible components may include:

- `mge_pot`
- `mge_lum`
- `disk_pot`
- `disk_lum`
- `kinematics`
- `populations`

Every included component must declare `parameters`.

Component parameters become namespaced internally by appending the component
name. For example, the `q` parameter on component `stars` becomes `q-stars`.

### system_parameters

System-level parameters include:

- `ml`: mass-to-light ratio. This must be the first system parameter.
- `omega`: optional, used for barred/rotating systems. If present, this must be
  the second system parameter.

The system currently rejects additional system parameters beyond `ml` and
optional `omega`.

### orblib_settings

This section controls orbit library construction.

Common settings seen in sample configs:

- `nE`: number of energy shells.
- `logrmin`, `logrmax`: radial range.
- `nI2`, `nI3`: integral grid dimensions.
- `dithering`: orbit dithering.
- `orbital_periods`: integration length.
- `sampling`: orbit sampling count.
- `starting_orbit`: first orbit index.
- `number_orbits`: number to integrate; `-1` means all orbits.
- `accuracy`: Fortran-style accuracy string in examples.
- `random_seed`: `<= 0` means stochastic seed in the example comments.

Validation enforces `nI2 >= 4`. Missing quadrature settings are defaulted:

- `quad_nr`: default `10`
- `quad_nth`: default `6`
- `quad_nph`: default `6`

### weight_solver_settings

This section chooses how orbital weights are solved.

Observed solver types:

- `NNLS`: active Python NNLS path.

`LegacyWeightSolver` is archived and rejected by current configuration
validation. Its old Fortran support sources are kept under
`archive/legacy_nnls_fortran/` for reference only.

Common settings:

- `type`
- `nnls_solver`
- `regularisation`
- `number_GH`
- `GH_sys_err`
- `lum_intr_rel_err`
- `sb_proj_rel_err`
- `reattempt_failures`
- `CRcut`
- `maxiter_factor` for SciPy NNLS

If `reattempt_failures` is omitted, `Configuration` defaults it to `True`.

If `nnls_solver` is `cvxopt` and the module is not installed, settings
validation raises `ModuleNotFoundError`.

### parameter_space_settings

This section chooses the parameter generator and stopping criteria.

Observed generator types:

- `LegacyGridSearch`
- `GridWalk`
- `FullGrid`
- `SpecificModels`

Common keys:

- `generator_type`
- `which_chi2`
- `generator_settings`
- `stopping_criteria`

Stopping criteria commonly include:

- `min_delta_chi2_abs`
- `min_delta_chi2_rel`
- `n_max_mods`
- `n_max_iter`

For `LegacyGridSearch`, `Configuration` can translate either an absolute
threshold or a threshold expressed as a fraction of `sqrt(2*nobs)` into
`threshold_del_chi2`.

### legacy_settings

`legacy_settings.directory` is retained for legacy configuration shape, but
the active orbit-library runtime uses `dynamite/orblib_api.py` and its shared
library path instead of this setting.

If the value is `default`, `Configuration` resolves it to the repository's
`orblib_fortran/build/lib` directory. A trailing slash is removed.

### io_settings

Required keys:

- `input_directory`
- `output_directory`
- `all_models_file`

`Settings.add("io_settings", values)` also derives:

- `model_directory = output_directory + "models/"`
- `plot_directory = output_directory + "plots/"`

`Configuration` creates these directories if they do not exist. If
`reset_existing_output=True` is passed to `Configuration`, the existing output
directory tree is deleted before creation.

### multiprocessing_settings

Controls parallelism and iterator type.

Observed/defaulted keys:

- `ncpus`: integer or `all_available`
- `ncpus_weights`: defaults to `ncpus`
- `ncpus_ext`: defaults to `ncpus`
- `modeliterator`: defaults to `ModelInnerIterator`
- `orblibs_in_parallel`: defaults to `False`

If running under Slurm, the code checks `SLURM_JOB_CPUS_PER_NODE` and may add
the current working directory to `sys.path`.

## Runtime Object Model

### Settings

`config_reader.Settings` is a plain container for the major config settings:

- `orblib_settings`
- `parameter_space_settings`
- `legacy_settings`
- `io_settings`
- `weight_solver_settings`
- `multiprocessing_settings`

It also validates expected sections and some solver/orbit-library details.

### System

`physical_system.System` represents the galaxy or stellar system. It owns:

- component list
- system-level parameters
- distance
- name
- counts of kinematic and population data sets

Validation checks:

- system has `distMPc` and `name`
- system has components
- first system parameter is `ml`
- optional second system parameter is `omega`
- no extra system parameters beyond those
- component structure is consistent

### Components

`physical_system.Component` is the base class. Subclasses specialize it:

- visible components carry MGE data and kinematics
- dark components provide potential/density/mass functions
- Plummer is used as a compact central component
- `Chi2Ext` delegates external chi-square calculation to a user-provided class

Components own their own parameter list. A component can validate both its
declared parameter names and a proposed parameter set.

### Parameters

`parameter_space.Parameter` represents one model parameter.

Important ideas:

- A parameter has a stored value.
- A parameter may be fixed or free.
- A parameter can be logarithmic.
- A parameter may carry generator settings such as `lo`, `hi`, `step`, and
  `minstep`.
- Raw values and physical parameter values can differ. The current explicit
  transformation is logarithmic conversion.

### ParameterSpace

`parameter_space.ParameterSpace` is a list of all parameters from:

1. every component
2. the system itself

It records:

- `par_names`
- total parameter count
- fixed/free parameter counts

It can:

- convert raw values to parameter values
- convert parameter values back to raw values
- find parameters by name
- produce a one-row Astropy table representing the current parameter set
- validate a candidate parameter set through the system and components

## Input Data Objects

### MGE

`mges.MGE` reads Multi Gaussian Expansion data. Visible components use:

- `mge_pot` for potential/mass density
- `mge_lum` for luminosity density

MGE methods support:

- validating observed axis ratios
- converting old formats
- calculating projected masses
- calculating intrinsic masses
- adding MGE objects for barred/disk combined luminosity cases

### Kinematics

`kinematics.Kinematics` is the base. Important subclasses:

- `GaussHermite`
- `BayesLOSVD`

Kinematics data can:

- read observed data
- validate and update data for solver settings
- convert to old Fortran-compatible formats
- transform orbit-library outputs into observables
- provide observed values and uncertainties for fitting

`GaussHermite` handles velocity, dispersion, and higher-order GH coefficients.
`BayesLOSVD` handles histogrammed LOSVD data and HDF5/ECSV conversion support.

### Populations

`populations.Populations` stores integrated population data. Population data is
used by orbit-coloring workflows and may be attached to visible components or
derived from kinematic data with population columns.

## Model Tracking: all_models.ecsv

`model.AllModels` manages the global model table.

The filename comes from:

```text
output_directory + all_models_file
```

The table includes:

- one column per parameter
- `chi2`
- `kinchi2`
- `kinmapchi2`
- optional `chi2_ext_added`
- `time_modified`
- `orblib_done`
- `weights_done`
- `all_done`
- `which_iter`
- `directory`

This table is the central checkpoint and resume mechanism.

`AllModels` can:

- create an empty table
- read a previous table from disk
- update stale/incomplete status by inspecting model directories
- detect existing orbit libraries
- detect existing weights
- add external chi-square where needed
- delete unusable incomplete model rows when configured not to retry failures
- save the table
- retrieve best models
- map rows to `Model` objects
- compute velocity-scaling factors when reusing orbit libraries across `ml`

The table is saved repeatedly during iteration so a failed run can often be
resumed or repaired.

## Model Directory Structure

Individual models live under:

```text
<output_directory>/models/
```

Directory names are assigned by `ModelInnerIterator.assign_model_directories`.

New orbit-library models use:

```text
orblib_<iteration>_<index>/ml<ml_value>/
```

Example shape:

```text
NGC6278_output/
  all_models.ecsv
  plots/
  models/
    orblib_000_000/
      datfil/
      ml05.00/
```

The `orblib_...` directory contains orbit-library files shared by all models
with the same orbit-library-defining parameters. The nested `ml...` directory
contains mass-to-light specific weight-solver output.

This distinction matters. Changing only `ml` can reuse the same orbit library
with velocity scaling, while other parameter changes require a new orbit
library.

## Model Object Lifecycle

`model.Model` represents one row of `all_models.ecsv`.

Initialization:

1. Receives `config` and `parset`.
2. Validates the parameter set against the parameter space.
3. Determines the model directory from `all_models.ecsv` unless explicitly
   provided.
4. Derives `directory_noml`, the shared orbit-library directory.
5. Warns if the current config file differs from a config backup in the model
   directory.

Main methods:

- `setup_directories()`: creates the model directory and `datfil/` output
  directory. The active direct-input runtime does not create `infil/`.
- `get_orblib()`: instantiates `LegacyOrbitLibrary`; its active generation path
  delegates to the direct shared-library backend.
- `get_weights(orblib)`: chooses and runs the configured weight solver.

`get_weights()` writes results back to the model object:

- `weights`
- `chi2`
- `kinchi2`
- `kinmapchi2`

## Parameter Generation

`ModelIterator` chooses a generator class from
`parameter_space_settings.generator_type`.

`ParameterGenerator.generate()` wraps every concrete generator:

1. Check stopping criteria.
2. Generate proposed parameter models through the subclass method.
3. Filter out already-run or invalid models.
4. Convert raw values to parameter values.
5. Add valid models to `AllModels.table`.
6. Update status.

Special behavior:

- If this is the first generation step, the generator may combine iterations
  0 and 1 by calling the specific generation method twice.
- A generated "model" in this layer is a list of `Parameter` objects, not a
  `model.Model` instance.

Generator classes:

- `LegacyGridSearch`: legacy-style parameter stepping around best models.
- `GridWalk`: walks a grid from a center point.
- `FullGrid`: enumerates a full grid.
- `SpecificModels`: runs explicitly listed parameter combinations.

## Model Iteration

`model_iterator.ModelIterator` is the high-level "run everything" object.

On construction it:

1. Reads parameter-space settings.
2. Instantiates the configured parameter generator.
3. Optionally creates a `Plotter`.
4. Instantiates the configured inner iterator, usually `ModelInnerIterator`.
5. Determines the previous iteration from `all_models.ecsv`.
6. Optionally reattempts failed weight solving.
7. Loops until `n_max_iter`, `n_max_mods`, no-new-models, or another stopping
   criterion stops the run.
8. After successful iterations, attempts plots.

`ModelInnerIterator.run_iteration()` is the core work loop:

1. Ask the parameter generator to add new rows to `AllModels`.
2. Save `AllModels` immediately after adding parameter rows.
3. Find new rows with empty `directory`.
4. Split rows into:
   - rows needing new orbit libraries
   - rows that can reuse an existing orbit library and only need weights
5. Assign model directory names.
6. Save `AllModels` again so directories survive failures.
7. Run model work in multiprocessing pools.
8. Write model results back into the table.
9. Optionally add external chi-square values.
10. Save `AllModels` again.

The iterator takes care to avoid computing the same orbit library twice when
multiple rows share orbit-library-defining parameters.

## Parallelism

DYNAMITE uses `pathos.multiprocessing.Pool` in the model iterator.

Relevant CPU settings:

- `ncpus`: orbit-library/model pool.
- `ncpus_weights`: weight-solving pool for split execution.
- `ncpus_ext`: external chi-square pool.
- `orblibs_in_parallel`: controls whether tube and box orbit-library work can
  be launched in parallel inside `LegacyOrbitLibrary`.

There are two execution modes in `run_iteration()`:

- default: run new orbit libraries and their weights together, then run
  remaining `ml`-only weights.
- split mode: run all orbit libraries first, then all weights, then external
  chi-square.

The default entry path uses the configured inner iterator. `SplitModelIterator`
exists as a specialized subclass.

## Orbit Library Generation

`orblib.LegacyOrbitLibrary` is still the object used by readers and weight
solvers, but active generation now delegates to
`dynamite/orblib_api.py`. The API facade exposes `OrbitLibraryRequest`,
`OrbitLibraryResult`, `run_orbit_library()`, and the
`fortran_shared_library` backend. `Model.get_orblib()` and
`LegacyOrbitLibrary.get_orblib()` use that backend for generation.

The shared backend calls
`orblib_fortran/build/lib/liborblib_fortran.so` through `ctypes`. Python passes
non-bar MGE potential arrays, viewing angles, black-hole parameters,
dark-halo parameters, orbit-grid settings, orbit-start arrays, PSF tables,
boxed-aperture geometry, velocity-histogram settings, bin maps, and output
paths directly to the C ABI. It does not create `parameters_pot.in`,
`orbstart.in`, `orblib.in`, `orblibbox.in`, `begin.dat`, or `beginbox.dat`, and
the active direct path intentionally preserves the legacy text-interface
precision for `parameters_pot` values and `begin` rows before handing data to
Fortran. The orbit-start worker runs in the model directory so the generated
`interpolgrid` cache is shared by the later tube and box shared-library workers.
This precision/cache behavior is part of the compatibility contract with the
historical executable-generated LOSVD fixture.

Important initialization inputs:

- `config`
- `mod_dir`: orbit-library directory without the `ml` subdirectory
- `parset`: model parameters

Important state:

- `system`
- `settings.orblib_settings`
- `legacy_directory`
- `input_directory`
- whether orbit libraries should run in parallel
- velocity scaling factor for models reusing an orbit library

`get_orblib()` does nothing if:

```text
datfil/tube_box_done
```

already exists in the orbit-library directory.

If the orbit library is missing, the active backend:

1. Extracts model, PSF, aperture, histogram, and binning inputs from Python
   configuration/data objects.
2. Calls `orblib_api_run_orbitstart_memory` to generate tube and box orbit
   starts in memory.
3. Calls `orblib_api_run_orblib_direct` for the tube and box libraries with
   those orbit-start arrays.
4. Compresses the generated binary `datfil/*_qgrid.dat` and
   `datfil/*_losvd_hist.dat` outputs to `.bz2`.
5. Calculates intrinsic masses through the Python MGE code for active NNLS
   weight solving.
6. Touches `datfil/tube_box_done` if both `tube_done` and `box_done` exist.

Generated files include:

- `orblib_qgrid.dat.bz2`
- `orblib_losvd_hist.dat.bz2`
- `orblib.dat_orbclass.out`
- `orblibbox_qgrid.dat.bz2`
- `orblibbox_losvd_hist.dat.bz2`
- `orblibbox.dat_orbclass.out`
- `mass_qgrid.ecsv`
- `mass_radmass.ecsv`

The direct-input shared-library path currently supports the non-bar triaxial
orbit-library route. The dark halo path supports zero or one non-Plummer dark
component; more than one non-Plummer dark component raises an error before
calling Fortran. Binary `datfil/` outputs remain because the existing Python
readers and weight solvers consume that format.

## Fortran Backend Relationship

The Python package treats `orblib_fortran/` as a shared-library numerical
backend for active orbit-library generation.

Active roles:

- generate orbit initial conditions
- integrate tube and box orbits
- build orbit libraries

Executable driver sources are retained under `orblib_fortran/source/unused/`
for historical reference. They are not part of the supported build, and normal
builds no longer create `orblib_fortran/bin/`.

The shared-library target is built with:

```bash
make -C orblib_fortran all
```

`make -C orblib_fortran shared` is equivalent. It writes
`orblib_fortran/build/lib/liborblib_fortran.so`. The exported ABI version is
`2` and includes `orblib_api_abi_version`,
`orblib_api_run_orbitstart_memory`, and `orblib_api_run_orblib_direct`.
Python isolates shared-library calls in worker processes by default because
the Fortran modules use global state and several legacy `STOP` paths can
terminate the calling process.

The old `triaxnnls_*` GALAHAD/NNLS solver sources and `triaxmass*`
mass-helper sources are archived under `archive/legacy_nnls_fortran/`. The
untested `orbgen`/`partgen` utilities are archived under
`archive/legacy_orbgen_partgen/`. They are not part of the active
`orblib_fortran` build.

## C++ Backend Experiment

The `fortran-to-cpp` branch adds an experimental C++ orbit-library backend
skeleton under `orblib_cpp/`. It is not the active default backend.

The shared-library target is built with:

```bash
make -C orblib_cpp shared
```

It writes `orblib_cpp/build/lib/liborblib_cpp.so`. The exported ABI version is
`1` and includes:

- `orblib_cpp_api_abi_version`
- `orblib_cpp_api_ran1_sequence`
- `orblib_cpp_api_elliptic_legendre`
- `orblib_cpp_api_triaxial_mge_setup`
- `orblib_cpp_api_triaxial_mge_evaluate`
- `orblib_cpp_api_potential_stack_evaluate`
- `orblib_cpp_api_interpolated_potential_evaluate`
- `orblib_cpp_api_orbit_rhs_evaluate`
- `orblib_cpp_api_classify_orbit_samples`
- `orblib_cpp_api_project_orbit_samples`
- `orblib_cpp_api_apply_psf`
- `orblib_cpp_api_find_boxed_aperture_pixels`
- `orblib_cpp_api_losvd_velocity_bins`
- `orblib_cpp_api_accumulate_losvd_histogram`
- `orblib_cpp_api_collapse_losvd_binning`
- `orblib_cpp_api_normalize_losvd_histogram`
- `orblib_cpp_api_sparse_losvd_ranges`
- `orblib_cpp_api_qgrid_boundaries`
- `orblib_cpp_api_accumulate_qgrid`
- `orblib_cpp_api_normalize_qgrid`
- `orblib_cpp_api_write_qgrid_file`
- `orblib_cpp_api_write_losvd_histogram_file`
- `orblib_cpp_api_write_population_mass_file`
- `orblib_cpp_api_write_orbit_class_file`
- `orblib_cpp_api_orbitstart_calc_start_state`
- `orblib_cpp_api_orbitstart_find_equivalent_radius`
- `orblib_cpp_api_integrate_orbit_final_state`
- `orblib_cpp_api_integrate_orbit_samples`
- `orblib_cpp_api_dop853_harmonic`
- `orblib_cpp_api_run_orbitstart_memory`
- `orblib_cpp_api_run_orblib_direct`

The first actual ported Fortran kernels are:

- `ran1_nr.f`, implemented in C++ as `dynamite::orblib_cpp::Ran1`. The class
  owns its shuffle table as fixed-size state and allocates no heap memory
  during `next()`. The C ABI helper `orblib_cpp_api_ran1_sequence` is used by
  tests to compare the C++ sequence against the existing Python/Fortran
  reference sequence.
- `numerics/dop853.f`, implemented in C++ as `dynamite::orblib_cpp::Dop853`.
  The solver preserves the DOP853 coefficient table, adaptive step controller,
  dense-output polynomial, status codes, and function/step counters while using
  reusable work arrays allocated before the integration loop. The C ABI helper
  `orblib_cpp_api_dop853_harmonic` is a test-only hook that integrates a
  harmonic oscillator and returns dense samples for Python-side validation.
- `numerics/ellipint.f90`, implemented as C++ Carlson RF/RD and Legendre
  incomplete elliptic integrals. The formulas match the Fortran routine, but
  the C++ convergence threshold is tightened because this setup-only kernel is
  not in the orbit hot loop and the original Fortran tolerances differ from
  SciPy by around `1e-8` for larger modulus cases.
- The non-bar `iniparam_from_arrays()` plus `tp_setup()` MGE setup/deprojection
  stage, implemented as `dynamite::orblib_cpp::TriaxialMgeSetup`. It converts
  observed MGE arrays and viewing angles into intrinsic `p/q`, intrinsic
  sigma, density, `V0`, triaxiality, and total mass. The C ABI helper
  `orblib_cpp_api_triaxial_mge_setup` is test-only and validates this setup
  against the Fortran formulas.
- The stellar triaxial MGE potential/acceleration evaluator from
  `tp_potent()` and `tp_accel()`. The current C++ evaluator covers the same
  per-Gaussian inner approximation, mid-radius integral, and far-field
  point-mass approximation, using a local adaptive Simpson integrator for the
  mid-radius path. The test-only C ABI helper
  `orblib_cpp_api_triaxial_mge_evaluate` validates representative points from
  all three regimes against independent Python/SciPy calculations of the
  Fortran formulas.
- The black-hole and supported dark-halo additions from `dmpotent.f90`,
  implemented as `dynamite::orblib_cpp::DarkHaloSetup` and the C++ potential
  stack in `orblib_cpp/source/potential.cpp`. This currently covers the
  Plummer-style black-hole term, dark-halo profiles 0 through 3, and profile 5
  gNFW: no halo, NFW, Hernquist, triaxial cored logarithmic, and gNFW. The
  profile 5 path also ports the unregularized incomplete-beta helper stack from
  `orblib_fortran/source/numerics/specfunc_beta.f90`. The test-only C ABI
  helper `orblib_cpp_api_potential_stack_evaluate` validates the combined
  stellar MGE, black-hole, and supported dark-halo terms against independent
  Python/SciPy calculations of the Fortran formulas, including gNFW gamma
  branches below, equal to, and above `1`.
- The in-memory acceleration interpolation math from `interpolpotent.f90`,
  implemented as `dynamite::orblib_cpp::InterpolatedPotential` in
  `orblib_cpp/include/interpolated_potential.hpp` and
  `orblib_cpp/source/interpolated_potential.cpp`. It preserves the Fortran
  radius-bound formulas, spherical-octant grid construction, endpoint angle
  offsets, log-acceleration storage, trilinear interpolation, and direct
  acceleration fallback outside the grid. The current C++ slice does not yet
  implement the legacy `interpolgrid` disk-cache read/write contract. The
  test-only C ABI helper `orblib_cpp_api_interpolated_potential_evaluate`
  validates metadata, direct potential, interpolated acceleration, and fallback
  counters against an independent Python implementation of the Fortran grid
  formulas.
- The orbit RHS derivative formula from `orblib_f_new_mirror.f90`'s `derivs`,
  implemented as `dynamite::orblib_cpp::evaluate_orbit_rhs` in
  `orblib_cpp/include/orbit_rhs.hpp` and `orblib_cpp/source/orbit_rhs.cpp`.
  It calls the C++ interpolated acceleration path and applies the same
  non-rotating derivative assignment and barred-frame `Omega` terms used by the
  Fortran orbit-library integrator. The test-only C ABI helper
  `orblib_cpp_api_orbit_rhs_evaluate` validates both `Omega == 0` and
  `Omega != 0` against independent Python calculations of the Fortran formulas.
- Single-orbit final-state DOP853 integration using the orbit RHS, implemented
  as `dynamite::orblib_cpp::integrate_orbit_final_state` in
  `orblib_cpp/include/orbit_integrator.hpp` and
  `orblib_cpp/source/orbit_integrator.cpp`. This is not the full orbit-library
  integrator yet: it does not perform LOSVD binning, qgrid accumulation, or
  output writing. The test-only C ABI helper
  `orblib_cpp_api_integrate_orbit_final_state` validates the DOP853/RHS wiring
  against SciPy DOP853 on an independent softened black-hole RHS.
- Prescribed dense-output sample extraction for a single orbit, implemented as
  `dynamite::orblib_cpp::integrate_orbit_samples`. It uses the C++ DOP853 dense
  output polynomial to return six-component orbit states at caller-provided
  sorted sample times while sharing the same RHS and interpolated-potential
  path as final-state integration. The test-only C ABI helper
  `orblib_cpp_api_integrate_orbit_samples` validates final state and sampled
  states against SciPy DOP853 dense output on the same independent softened
  black-hole RHS.
- Orbit classification and moment calculation from
  `integrator_find_orbtype()` in `orblib_f_new_mirror.f90`, implemented as
  `dynamite::orblib_cpp::classify_orbit_samples` in
  `orblib_cpp/include/orbit_classification.hpp` and
  `orblib_cpp/source/orbit_classification.cpp`. It preserves the Fortran
  angular-momentum sign-crossing type rules for X tubes, Y tubes, Z tubes,
  boxes, and stochastic orbits, plus the five `moments` values and three
  cylindrical velocity-dispersion `moments2` values. The test-only C ABI helper
  `orblib_cpp_api_classify_orbit_samples` validates all five orbit type
  outcomes and moment arrays against a Python mirror of the Fortran formulas.
- Per-symmetry projection and line-of-sight velocity calculation from
  `project_n()` in `orblib_f_new_mirror.f90`, implemented as
  `dynamite::orblib_cpp::project_orbit_samples` in
  `orblib_cpp/include/orbit_projection.hpp` and
  `orblib_cpp/source/orbit_projection.cpp`. It preserves the Fortran position
  and velocity sign tables for all five orbit types, all eight projection
  symmetries, and both `Omega == 0` and `Omega != 0` paths. The test-only C ABI
  helper `orblib_cpp_api_project_orbit_samples` validates projected coordinates
  and LOS velocities against a Python mirror of the Fortran formulas.
- PSF Gaussian convolution from the Fortran `psf` module, implemented as
  `dynamite::orblib_cpp::apply_psf_to_projected_samples` in
  `orblib_cpp/include/orbit_psf.hpp` and `orblib_cpp/source/orbit_psf.cpp`.
  It preserves the tiny-sigma copy-through branch, single-Gaussian convolution
  branch, MGE-PSF weighted sigma-map construction, `Ran1` selector draws, and
  the single-precision Gaussian deviate path used by the Fortran code. The
  test-only C ABI helper `orblib_cpp_api_apply_psf` validates those branches
  against a Python mirror of the Fortran formulas.
- Boxed aperture pixel lookup from `aperture_boxed_find()` in
  `orblib_f_new_mirror.f90`, implemented as
  `dynamite::orblib_cpp::find_boxed_aperture_pixels` in
  `orblib_cpp/include/orbit_aperture.hpp` and
  `orblib_cpp/source/orbit_aperture.cpp`. It preserves the Fortran
  `-aperture_rotation + pi/2 - psi_proj` rotation, conversion-factor scaling,
  strict box bounds, and 1-based `xbin + ybin * bins_x + 1` flattening. The
  test-only C ABI helper `orblib_cpp_api_find_boxed_aperture_pixels` validates
  interior bins, bin transitions, and boundary exclusions against a Python
  mirror of the Fortran formula.
- LOSVD velocity-bin mapping and per-aperture histogram accumulation from
  `histogram_velbin()` and `histogram_store()` in `orblib_f_new_mirror.f90`,
  implemented as `dynamite::orblib_cpp::map_losvd_velocity_bins` and
  `dynamite::orblib_cpp::accumulate_losvd_histogram` in
  `orblib_cpp/include/orbit_histogram.hpp` and
  `orblib_cpp/source/orbit_histogram.cpp`. The port preserves the Fortran
  lower/upper velocity clamp behavior, strict interior velocity-bin bounds,
  1-based velocity bins, zero aperture-pixel skip, and full-sample
  normalization counter increment. Test-only C ABI helpers
  `orblib_cpp_api_losvd_velocity_bins` and
  `orblib_cpp_api_accumulate_losvd_histogram` validate those rules against
  Python mirrors of the Fortran formulas.
- LOSVD bin-order collapsing, normalization, and sparse row-range preparation
  from `binning_add_it_up()`, `histogram_write()`, and
  `histogram_write_compat_sparse()` in `orblib_f_new_mirror.f90`, implemented
  as `dynamite::orblib_cpp::collapse_losvd_binning`,
  `dynamite::orblib_cpp::normalize_losvd_histogram`, and
  `dynamite::orblib_cpp::compute_sparse_losvd_ranges`. The port preserves
  bin-order `0` discard behavior, many-to-one aperture-bin summation,
  reciprocal normalization for positive stored counts, zeroing for nonpositive
  stored counts, and the Fortran sparse begin/end velocity-offset convention.
  Test-only C ABI helpers `orblib_cpp_api_collapse_losvd_binning`,
  `orblib_cpp_api_normalize_losvd_histogram`, and
  `orblib_cpp_api_sparse_losvd_ranges` validate the memory-side preparation.
  Sparse LOSVD Fortran-record binary serialization is implemented as
  `dynamite::orblib_cpp::write_losvd_histogram_file` in
  `orblib_cpp/include/orbit_output.hpp` and
  `orblib_cpp/source/orbit_output.cpp`. The test-only C ABI helper
  `orblib_cpp_api_write_losvd_histogram_file` validates the mixed setup record,
  sparse begin/end records, and optional value records through SciPy
  `FortranFile`. Full orbit-engine wiring remains unported.
- Intrinsic qgrid boundary setup, moment accumulation, orbit-type channel
  accumulation, and normalization from `qgrid_setup()`, `qgrid_store()`, and
  `qgrid_write()` in `orblib_f_new_mirror.f90`, implemented in
  `orblib_cpp/include/orbit_qgrid.hpp` and
  `orblib_cpp/source/orbit_qgrid.cpp`. The port preserves the Fortran radial
  and angular boundary formulas, `hunt`-style equality behavior on inner
  boundaries, non-rotating and rotating-frame symmetry sign tables,
  positive-octant filtering, 16-channel accumulation layout, orbit-type
  channel mapping, per-cell moment normalization, and global light/type
  normalization. Test-only C ABI helpers `orblib_cpp_api_qgrid_boundaries`,
  `orblib_cpp_api_accumulate_qgrid`, and `orblib_cpp_api_normalize_qgrid`
  validate the memory-side qgrid math.
- Qgrid Fortran-record binary serialization, implemented as
  `dynamite::orblib_cpp::write_qgrid_file` in
  `orblib_cpp/include/orbit_output.hpp` and
  `orblib_cpp/source/orbit_output.cpp`. It writes the same record order used
  by `integrator_setup_write()`, `qgrid_setup_write()`,
  `integrator_write()`, and `qgrid_write()` for the split
  `*_qgrid.dat` output files. The test-only C ABI helper
  `orblib_cpp_api_write_qgrid_file` validates the generated file through
  SciPy `FortranFile`.
- Population projected-mass Fortran-record binary serialization, implemented
  as `dynamite::orblib_cpp::write_population_mass_file` in
  `orblib_cpp/include/orbit_output.hpp` and
  `orblib_cpp/source/orbit_output.cpp`. It writes one real-valued record per
  orbit and population aperture vector, matching the existing Python
  `*_pops.dat` reader. The test-only C ABI helper
  `orblib_cpp_api_write_population_mass_file` validates the records through
  SciPy `FortranFile`.
- Formatted orbit-class output, implemented as
  `dynamite::orblib_cpp::write_orbit_class_file` in
  `orblib_cpp/include/orbit_output.hpp` and
  `orblib_cpp/source/orbit_output.cpp`. It writes the same moment-major,
  dither-next, orbit-next token order expected by
  `read_orbit_property_file_base()`'s `reshape(..., order='F')` path. The
  test-only C ABI helper `orblib_cpp_api_write_orbit_class_file` validates the
  generated text file against that Python reader contract.
- Direct-potential orbit-start kernels from `orbitstart_f.f90`, implemented as
  `dynamite::orblib_cpp::calculate_orbit_start_state` and
  `dynamite::orblib_cpp::find_equivalent_radius` in
  `orblib_cpp/include/orbit_start.hpp` and
  `orblib_cpp/source/orbit_start.cpp`. The first preserves
  `calc_startpos()`'s x/z placement, zero vx/vz, positive-y velocity formula,
  and tiny fallback for negative or NaN kinetic terms. The second preserves
  `findReq()`'s bisection range, potential comparison, `1e-7` relative
  potential stopping rule, and 60000-iteration cap. Test-only C ABI helpers
  `orblib_cpp_api_orbitstart_calc_start_state` and
  `orblib_cpp_api_orbitstart_find_equivalent_radius` validate these formulas
  against independent Python mirrors. The same module also ports
  `find_unregorbits()` and the radius/noreg scheduling part of
  `make_startpoints()` as
  `dynamite::orblib_cpp::compute_unregularized_orbit_grid` and
  `dynamite::orblib_cpp::compute_tube_start_schedule`; ABI tests validate the
  reverse `nI2` propagation scan, irregular-energy boundary replacement, and
  nearly closed-boundary sampling formula. `make_boxstartpoints()`'s
  per-record angular-grid and Cartesian record construction is ported as
  `dynamite::orblib_cpp::calculate_box_start_record`, reusing
  `find_equivalent_radius()` and preserving the zero-velocity and
  circular-orbit metadata fields. The full `make_boxstartpoints()` loop is
  ported as `dynamite::orblib_cpp::build_box_start_records`, producing
  flattened `[energy, nI2, nI3, 9]` records plus all-zero noreg flags. The
  boundary-search routines, tube begin-array generation, and full runtime
  orbit-start orchestration are not ported yet.

The Python API facade accepts backend name `cpp_shared_library`. Read-only
requests with `generate_if_missing=False` can use the same existing Python
orbit-library readers as the Fortran backend. Generation calls currently enter
the C++ shared library and return status `-100`, meaning the C++ orbit engine is
not implemented yet. This is intentional: the first slice establishes the
compiled ABI, build target, Python selection path, and hard failure boundary
without silently falling back to Fortran.

The default backend remains `fortran_shared_library` until the C++ backend
matches the Fortran-derived fixtures and passes the planned parity tests.

## Weight Solving

`weight_solvers.WeightSolver` is the base class. The active implementation is:

- `NNLS`

The `LegacyWeightSolver` source remains in `dynamite/weight_solvers.py` for
historical reference, but configuration validation and `Model.get_weights()`
reject it because its Fortran helpers are archived.

The solver stage finds non-negative orbital weights that best reproduce the
observations and mass constraints.

Returned values are:

- `weights`
- `chi2_tot`
- `chi2_kin`
- `chi2_kinmap`

These become:

- `Model.weights`
- `Model.chi2`
- `Model.kinchi2`
- `Model.kinmapchi2`

### Archived LegacyWeightSolver

The old Python `LegacyWeightSolver` class called Fortran NNLS-style programs:

- `triaxnnls_CRcut`
- `triaxnnls_noCRcut`
- barred variants where applicable

It prepared old-format kinematic input files, wrote `nn.in`, ran the solver,
and read the solver outputs. This path is no longer active.

It supports the `CRcut` setting for the counter-rotating orbit problem.

Those Fortran executables are archived rather than active in the current tree.
Do not select this solver path as an active runtime path unless it is
explicitly restored or pointed at a controlled archived build.

### NNLS

The Python `NNLS` class constructs an NNLS matrix and right-hand side using:

- observed mass constraints
- orbit-library projections
- kinematic constraints
- regularization settings

It can use SciPy's NNLS implementation or optional `cvxopt`, depending on
configuration.

### chi2_kinmap

The base class provides `chi2_kinmap(weights)`, which directly compares model
kinematic maps to observed maps for `GaussHermite` kinematics. If any
kinematic data are not `GaussHermite`, it returns `nan` and logs why.

## External Chi-Square

`physical_system.Chi2Ext` allows a config to plug in an external module/class
for additional chi-square contributions.

When present:

- `AllModels` adds a `chi2_ext_added` column.
- `ModelInnerIterator` can run external chi-square after weights.
- The external chi-square is added to `chi2`, `kinchi2`, and `kinmapchi2`.

Rows that differ only in external chi-square parameters can avoid redundant
orbit-library or weight work.

## Plotting And Analysis

`plotter.Plotter` is optionally created by `ModelIterator`.

After successful iterations, plotting attempts include:

- chi-square versus model id
- chi-square parameter plots
- kinematic maps for the best model so far

Plotting failures are logged as warnings and do not necessarily stop modelling.

`analysis.Analysis` and `analysis.Decomposition` support post-processing such
as:

- extracting projected/intrinsic model quantities
- building kinematic maps
- orbit decomposition
- orbit-distribution and anisotropy analysis

`coloring.Coloring` supports stellar-population or orbit-coloring workflows.

## Output Files Are State

DYNAMITE uses disk output as durable state. This matters when debugging.

Key state files and directories:

- `<output_directory>/<all_models_file>`
- `<output_directory>/models/`
- `<output_directory>/plots/`
- model-specific YAML config backups
- `datfil/` orbit-library data and status files
- weight files under the `ml.../` directory

Do not treat outputs as disposable unless the task explicitly says to reset or
delete them. `Configuration(reset_existing_output=True)` can delete the output
tree, but normal construction preserves existing data.

## Failure And Resume Behavior

DYNAMITE has explicit support for partially completed runs.

During `Configuration`:

- existing `all_models.ecsv` is loaded if present
- orbit-library flags are updated by inspecting directories
- model-table status is repaired where possible

During `ModelIterator`:

- `reattempt_failures=True` causes failed weights to be retried if orbit
  libraries exist
- rows with no usable orbit library and no weights may be removed
- existing orbit libraries can be reused

This means a failed run is often recoverable without recomputing everything.
It also means table state and directory state must be kept consistent.

## Important Scientific Assumptions

This section summarizes the local audit perspective.

The core non-rotating triaxial Schwarzschild/MGE modelling chain appears
scientifically grounded. The main caveats from the local audits are:

- convergence and stopping criteria require careful interpretation
- barred-model support needs benchmarking caution
- cored-log halo density domains need attention
- modelling priors influence results
- failure handling in orblib Fortran paths may be weak
- solver status should be checked carefully
- build and dependency environments matter

For detailed audit notes, see:

- `aidocs/audits/dynamite_python_audit.md`
- `aidocs/audits/dynamite_fortran_audit.md`
- `aidocs/audits/dynamite_scientific_correctness_audit.md`

## Development And Modification Guidance

When modifying this fork:

1. Read `AGENTS.md`.
2. Read `aidocs/KNOWLEDGE.md`.
3. Keep local AI notes in `aidocs/`.
4. Avoid editing upstream `docs/` unless explicitly asked.
5. Avoid editing `orblib_fortran/` unless the task is specifically about the
   Fortran backend.
6. Avoid editing `archive/dev_tests/` unless the task is specifically about
   archived tests or examples.
7. Check `git status --short` before and after edits.
8. Prefer small, focused changes.
9. Treat existing uncommitted user changes as intentional.
10. Run the narrowest useful verification for any code change.

For documentation-only changes inside `aidocs/`, code tests are usually not
necessary.

## Useful Read-Only Inspection Commands

These commands are useful when orienting future work:

```bash
git remote -v
git status --short
rg -n "class ModelIterator|class Configuration|class Model|class AllModels" dynamite
rg -n "generator_type|weight_solver_settings|orblib_settings" dev_tests docs
find aidocs -maxdepth 3 -type f -print
```

## Common Places To Inspect

For config parsing:

- `dynamite/config_reader.py`

For system and components:

- `dynamite/physical_system.py`

For parameter generation:

- `dynamite/parameter_space.py`

For model tracking and directories:

- `dynamite/model.py`

For the high-level run loop:

- `dynamite/model_iterator.py`

For orbit libraries:

- `dynamite/orblib.py`

For weight solving:

- `dynamite/weight_solvers.py`

For observed data:

- `dynamite/data.py`
- `dynamite/mges.py`
- `dynamite/kinematics.py`
- `dynamite/populations.py`

For plotting and post-processing:

- `dynamite/plotter.py`
- `dynamite/analysis.py`
- `dynamite/coloring.py`

## Practical Workflow For Future Agents

For a normal code task:

1. Confirm the task scope and allowed write areas.
2. Inspect `git status --short`.
3. Read `aidocs/KNOWLEDGE.md`.
4. Read the relevant source module.
5. Make the smallest scoped edit.
6. Update `aidocs/KNOWLEDGE.md` and `aidocs/CHANGES.md` if behavior,
   workflow, architecture, dependencies, or operational knowledge changed.
7. Run focused tests or static checks if code changed.
8. Report exactly what changed and what was not tested.

For a documentation-only task like this one:

1. Keep edits in `aidocs/`.
2. Do not touch upstream `docs/`, package code, orblib Fortran, or dev tests.
3. Update the local index and current-state files.
4. Verify no forbidden paths changed with `git status --short`.

## Current Local State After This Documentation Pass

Expected local untracked documentation additions:

```text
AGENTS.md
aidocs/
```

No upstream source, upstream docs, orblib Fortran, or dev-test files should be
modified by this documentation pass.

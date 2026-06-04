# DYNAMITE Code Map

## Repository Layout

```text
dynamite/
  dynamite/          Main Python package
  orblib_fortran/    Active Fortran orbit-library backend
    source/          Human-written Fortran source
    build/lib/       Ignored generated shared library
  archive/           Archived dev tests and legacy Fortran solver/utilities
  docs/              Sphinx docs, API docs, tutorials, images, notebooks
  setup.py           Python packaging metadata
  requirements.txt   Python dependency list
  README.md          Short project description and basic install/use notes
```

## Main Runtime Flow

The normal runtime entry point is a small Python script written by the user:

```python
import dynamite as dyn

c = dyn.config_reader.Configuration("config_file.yaml")
_ = dyn.model_iterator.ModelIterator(c)
```

The important control flow is:

```text
Configuration
  -> System / components / observed data
  -> ParameterSpace
  -> ModelIterator
  -> Model
  -> LegacyOrbitLibrary
  -> WeightSolver
  -> all_models.ecsv + plots + model directories
```

## Core Concepts

### Configuration

`dynamite/config_reader.py`

Reads the YAML config and turns it into runtime objects. It validates required
settings, creates output directories, reads model components, and prepares the
parameter space.

The config controls:

- Input/output directories.
- Physical system components.
- Potential parameters.
- Orbit-library settings.
- Weight-solver settings.
- Multiprocessing settings.
- Parameter iteration strategy.

### Physical System

`dynamite/physical_system.py`

Defines the galaxy/system being modelled. A `System` contains components such as:

- Visible triaxial stellar component.
- Bar/disk component.
- Plummer component, often used for central compact mass behaviour.
- Dark-matter halos such as NFW, Hernquist, cored logarithmic, and generalized
  NFW forms.
- Optional external chi-square components.

The system also owns the list of model parameters.

### Observational Data

Relevant modules:

- `dynamite/data.py`
- `dynamite/mges.py`
- `dynamite/kinematics.py`
- `dynamite/populations.py`

The code reads astronomy data formats such as Astropy ECSV tables and FITS-like
data products. The most important data types are:

- MGE light/mass profiles.
- Kinematic maps or LOSVD histograms.
- Aperture and binning descriptions.
- Optional population data.

### Parameter Space

`dynamite/parameter_space.py`

Defines model parameters and parameter-generation strategies. The code supports
several generator classes, including:

- `LegacyGridSearch`
- `GridWalk`
- `FullGrid`
- `SpecificModels`

These decide which model parameter combinations should be run.

### Models And Model Tracking

`dynamite/model.py`

Defines individual models and the global table of models already run.

The `AllModels` class manages `all_models.ecsv`, which records:

- Parameter values.
- Chi-square values.
- Whether orbit libraries were completed.
- Whether weights were solved.
- Whether the full model is done.
- The model output directory.

This allows runs to resume, reuse existing orbit libraries, or reattempt failed
weight calculations.

### Model Iterator

`dynamite/model_iterator.py`

Drives the full modelling loop. It creates parameter sets, runs models, checks
stopping criteria, retries failed weight solving if configured, and optionally
creates plots after iterations.

This is the closest thing to the high-level "run everything" engine.

### Orbit Libraries

`dynamite/orblib.py`

Creates orbit libraries for a model. The main implementation is
`LegacyOrbitLibrary`, which now delegates active generation to
`dynamite/orblib_api.py`. The shared-library backend passes Python-owned arrays
and scalars into `orblib_fortran/build/lib/liborblib_fortran.so`; it does not
write Fortran `infil/` input files or launch the orbit executables for normal
generation.

Generated output includes files such as:

- Tube and box qgrid/LOSVD orbit-library files.
- Orbit classifications.
- Intrinsic mass tables.
- Status files indicating completed tube/box orbit calculations.

### Weight Solvers

`dynamite/weight_solvers.py`

Solves for the non-negative orbital weights that best reproduce observed
kinematics.

Solver options include:

- `NNLS`: Python-based non-negative least-squares approach, using SciPy or
  optionally cvxopt.

`LegacyWeightSolver` is archived and rejected by the active configuration
path; its old Fortran support sources live under `archive/legacy_nnls_fortran/`.

This stage produces chi-square values that are used to compare models.

### Plotting And Analysis

Relevant modules:

- `dynamite/plotter.py`
- `dynamite/analysis.py`
- `dynamite/coloring.py`

These modules produce diagnostic plots and derived science products, including:

- Kinematic map comparisons.
- Chi-square progress plots.
- Mass profiles.
- Orbit distributions.
- Anisotropy and intrinsic-shape plots.
- Population/coloring analysis.

## Installation Shape

The current local README describes a two-stage active installation:

1. Compile the active Fortran shared library in `orblib_fortran/`.
2. Install the Python package with `python -m pip install .`.

The active Fortran build writes only the shared library to
`orblib_fortran/build/lib/`. Temporary object/module directories may be created
during compilation, but they are not runtime artifacts. Executable driver
sources are retained in `orblib_fortran/unused/` for reference.

## Things To Know Before Working On It

- The repo is large partly because it retains archived old Fortran optimization
  code and test data, not because the Python package is huge.
- Many important runtime behaviours depend on files written to disk, not only
  in-memory Python objects.
- The output directory is part of the modelling state; reruns may reuse or
  update existing model outputs.
- Real runs can consume significant disk space because orbit libraries are
  large.
- The codebase mixes modern Python orchestration with legacy compiled numerical
  code exposed through a direct shared-library ABI.
- Archived tests and examples in `archive/dev_tests/` are useful references for
  working configurations.

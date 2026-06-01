# DYNAMITE Code Map

## Repository Layout

```text
dynamite/
  dynamite/          Main Python package
  legacy_fortran/    Fortran numerical backend and bundled solver code
  docs/              Sphinx docs, API docs, tutorials, images, notebooks
  dev_tests/         Development tests, configs, sample data, notebooks
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
`LegacyOrbitLibrary`, which prepares input files for the Fortran backend and
then runs the legacy orbit programs.

Generated output includes files such as:

- Orbit initial conditions.
- Tube and box orbit libraries.
- Orbit classifications.
- Intrinsic mass tables.
- Status files indicating completed tube/box orbit calculations.

### Weight Solvers

`dynamite/weight_solvers.py`

Solves for the non-negative orbital weights that best reproduce observed
kinematics.

Solver options include:

- `LegacyWeightSolver`: calls legacy Fortran NNLS-style code.
- `NNLS`: Python-based non-negative least-squares approach, using SciPy or
  optionally cvxopt.

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

The README describes a three-stage full installation:

1. Install GALAHAD from `legacy_fortran/galahad-2.3/`.
2. Compile the Fortran programs in `legacy_fortran/`.
3. Install the Python package with `python -m pip install .`.

There is also documentation for using the Python NNLS solvers without the full
legacy GALAHAD path in some cases, but the repository is clearly designed around
a compiled numerical backend.

## Things To Know Before Working On It

- The repo is large because it vendors old Fortran optimization code and test
  data, not because the Python package is huge.
- Many important runtime behaviours depend on files written to disk, not only
  in-memory Python objects.
- The output directory is part of the modelling state; reruns may reuse or
  update existing model outputs.
- Real runs can consume significant disk space because orbit libraries are
  large.
- The codebase mixes modern Python orchestration with legacy compiled numerical
  executables.
- Tests and examples in `dev_tests/` are likely the fastest way to understand
  working configurations.


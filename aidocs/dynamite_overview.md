# DYNAMITE Repository Overview

## What This Project Is

DYNAMITE stands for **DYnamics, Age and Metallicity Indicators Tracing Evolution**.
It is a scientific astronomy package for modelling stellar systems, especially
galaxies, with Schwarzschild orbit-superposition methods and stellar-population
information.

In practical terms, DYNAMITE takes observational data for a galaxy, builds many
candidate dynamical models, generates orbit libraries for those models, solves
for the orbit weights that best reproduce the observed data, and then compares
the resulting model fits.

The package is aimed at research users rather than general application users.
It expects astronomy-specific input files and produces model tables, orbit
libraries, plots, and diagnostic output.

## Main Scientific Purpose

DYNAMITE is used to infer galaxy properties from observations. Typical modelling
targets include:

- Stellar mass-to-light ratio.
- Black hole mass.
- Dark matter halo parameters.
- Galaxy shape and viewing geometry.
- Orbit distributions.
- Kinematic structure.
- Stellar-population quantities such as age and metallicity.

The core modelling approach is orbit-based. Instead of assuming a simple analytic
distribution for stellar motion, the code creates a large library of possible
stellar orbits in a trial gravitational potential. It then finds a non-negative
combination of those orbits whose projected properties match the observed galaxy
data.

## Languages And Technology

The project is mainly written in **Python**, with a substantial **Fortran**
numerical backend.

Important language split:

- `dynamite/`: main Python package.
- `orblib_fortran/`: active Fortran 77/90 programs used for orbit initial
  conditions, orbit libraries, and mass calculations. Human-written source is
  under `orblib_fortran/source/`; compiled artifacts go to ignored `build/`
  and `bin/` folders.
- `archive/legacy_nnls_fortran/`: archived legacy NNLS/GALAHAD solver sources.
- `archive/legacy_orbgen_partgen/`: archived untested particle/orbit export
  utilities.
- `docs/`: Sphinx documentation and tutorial notebooks.
- `archive/dev_tests/`: archived development tests, example configs, sample
  data, and notebooks.

The Python package requires **Python 3.10 or newer** according to `setup.py`.
The current version in this checkout is **5.0.0**.

The active Fortran orbit-library side is not optional for full traditional
orbit-library generation. The current local no-GALAHAD build compiles the active
orblib programs in `orblib_fortran/`; archived solver sources are retained for
reference and compatibility work.

## Major Python Dependencies

The Python dependencies show the scientific-computing nature of the project.
Notable packages include:

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
- astronomy/binning packages such as `vorbin`, `plotbin`, `powerbin`, and `pafit`

Optional/testing dependencies include `pytest`, `coverage`, and `cvxopt`.

## Typical Input Data

A DYNAMITE run is driven by a YAML configuration file plus observational input
files. The docs describe a typical run directory containing:

- `config_file.yaml`: main modelling configuration.
- `input_files/mge.ecsv`: Multi Gaussian Expansion of stellar surface density.
- `input_files/kinematics.ecsv`: observed kinematic data.
- `input_files/bins.dat`: spatial binning information.
- `input_files/aperture.dat`: aperture/grid information.

The project supports different kinematic data styles:

- Gauss-Hermite kinematic moments.
- Histogrammed line-of-sight velocity distributions from BayesLOSVD.

Population data can also be used for "orbit coloring", where orbits receive
stellar-population attributes such as age, metallicity, or line-strength
information.

## Typical Output

A run creates an output tree with model directories, plots, and summary tables.
The docs describe outputs such as:

- `output/models/`: generated model directories and orbit-library files.
- `output/plots/`: diagnostic plots.
- `output/all_models.ecsv`: table summarizing models run so far.
- `output/mass_aper.ecsv`: projected mass data for some solver modes.
- `dynamite.log`: run log.

Orbit libraries can be large. The installation docs mention that real model runs
may require tens of gigabytes of disk space, even though the source code itself
is much smaller.

## How The Workflow Fits Together

At a high level, a DYNAMITE run does this:

1. Read a YAML configuration through `dynamite.config_reader.Configuration`.
2. Build a physical system object representing the galaxy and its components.
3. Read observational data such as MGE light profiles and kinematic maps.
4. Define a parameter space for model quantities such as mass-to-light ratio,
   black hole mass, dark halo parameters, and viewing geometry.
5. For each parameter set, create a `Model`.
6. Generate an orbit library for that model.
7. Solve for orbit weights that best reproduce the observed data.
8. Store chi-square values and model status in `all_models.ecsv`.
9. Iterate over parameter space until stopping criteria are met.
10. Produce diagnostic plots and derived analysis products.

The README's minimal usage example is:

```python
import dynamite as dyn

c = dyn.config_reader.Configuration("my_config.yaml")
_ = dyn.model_iterator.ModelIterator(c)
```

That simple call hides a lot of work: configuration parsing, model generation,
orbit calculation, weight solving, output bookkeeping, and plotting.

## Important Source Modules

The most important Python modules are:

- `config_reader.py`: reads YAML configs, validates settings, creates output
  directories, and builds the modelling system.
- `physical_system.py`: defines systems and components such as stars, black
  holes, dark matter halos, triaxial components, and barred disk systems.
- `parameter_space.py`: defines model parameters and algorithms for generating
  new parameter sets.
- `model.py`: represents individual models and tracks the `all_models.ecsv`
  table.
- `model_iterator.py`: drives iterative model creation and execution.
- `orblib.py`: creates orbit libraries, mostly by preparing inputs and calling
  legacy Fortran executables.
- `weight_solvers.py`: solves for non-negative orbit weights using either
  legacy Fortran solvers or Python NNLS-based solvers.
- `kinematics.py`: handles kinematic data formats such as Gauss-Hermite and
  BayesLOSVD data.
- `mges.py`: handles Multi Gaussian Expansion data.
- `plotter.py`: creates diagnostic and science plots.
- `analysis.py`: post-processing and derived analysis.
- `coloring.py` and `populations.py`: stellar-population/orbit-coloring support.

## Fortran Backend

The active `orblib_fortran/` directory contains the compiled orbit-library
backend. It includes source for:

- Orbit initial condition generation.
- Orbit integration.
- Orbit library construction.
- Triaxial mass calculations.

The Python code often acts as an orchestration layer around these compiled
programs: it writes input files, runs the executables, reads their outputs, and
stores the results in a structured project output tree.

Legacy NNLS/GALAHAD solver code now lives under `archive/legacy_nnls_fortran/`
instead of the active build tree.

## Documentation And Examples

The repo includes substantial documentation in `docs/`, including:

- Installation instructions.
- Configuration reference.
- Code overview.
- API documentation.
- Tutorial notebooks.
- Example input files for real or test galaxies.

The archived `archive/dev_tests/` directory contains practical examples and
tests. It is useful for seeing realistic configuration files and expected input
formats.

## Practical Impression

This is not a small Python-only library. It is a research software package that
wraps a mature numerical modelling workflow. The Python code provides the user
interface, data handling, iteration logic, plotting, and newer solver support.
The Fortran code provides expensive legacy numerical routines used for the
actual dynamical modelling.

The package is probably most useful to astronomers or researchers who already
have galaxy photometry/kinematics data and want to fit dynamical models. Running
it properly requires compiled Fortran tools, careful configuration, and enough
disk space for large orbit libraries.

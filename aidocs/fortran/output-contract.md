# Fortran Output Contract

Last updated: 2026-06-04

Purpose: describe the generated files and Python reader expectations for the
active Fortran orbit-library backend.

## Model Output Directory

Orbit-library generation writes into:

```text
<model>/datfil/
```

Tube file root:

```text
orblib
```

Box file root:

```text
orblibbox
```

## Raw Fortran Outputs

For each root, Fortran writes:

```text
datfil/<root>_qgrid.dat
datfil/<root>_losvd_hist.dat
datfil/<root>_pops.dat
datfil/<root>.dat_orbclass.out
datfil/<root>_qgrid.dat.tmp
```

`<root>_pops.dat` is relevant when population apertures exist. Not every model
has useful population output.

## Python-Compressed Outputs

After successful Fortran calls, Python compresses binary files:

```text
datfil/<root>_qgrid.dat.bz2
datfil/<root>_losvd_hist.dat.bz2
datfil/<root>_pops.dat.bz2
```

The orbit-class file remains text:

```text
datfil/<root>.dat_orbclass.out
```

Do not change compression behavior without updating Python readers and tests.

## Completion Markers

Python writes:

```text
datfil/tube_done
datfil/box_done
datfil/tube_box_done
```

Meaning:

- `tube_done`: tube orbit-library files were generated.
- `box_done`: box orbit-library files were generated.
- `tube_box_done`: high-level marker that the complete orbit library exists.

`Model` state uses `tube_box_done` as the main completion indicator.

## Python Readers

Reader implementation:

```text
dynamite/orblib.py
```

Important methods:

- `LegacyOrbitLibrary.read_orbit_base(...)`
- `LegacyOrbitLibrary.read_losvd_histograms(...)`
- `LegacyOrbitLibrary.read_orbit_intrinsic_moments(...)`
- `LegacyOrbitLibrary.read_orbit_property_file(...)`

Reader expectations:

- qgrid and LOSVD files exist as `.bz2` files for active new-format output.
- tube and box roots are read separately and then combined.
- the binary record ordering matches the Fortran writer.
- qgrid headers, dimensions, and orbit counts are consistent with LOSVD
  histogram records.
- optional population outputs are read only when population data and aperture
  mappings require them.

## QGrid File Contract

The qgrid file stores intrinsic 3D information and orbit properties.

Fortran writers:

```text
quadrantgrid.qgrid_setup_write()
quadrantgrid.qgrid_write()
output.output_write()
```

Python readers:

```text
LegacyOrbitLibrary.read_orbit_base()
LegacyOrbitLibrary.read_orbit_intrinsic_moments()
```

Contractual content includes:

- qgrid shape and coordinate layout
- orbit count
- intrinsic moment arrays
- orbit class/property linkage
- consistent tube/box concatenation behavior

## LOSVD Histogram Contract

The LOSVD histogram file stores projected orbit mass in velocity bins and
spatial apertures.

Fortran writers:

```text
histograms.histogram_store()
histograms.histogram_write()
output.output_write()
```

Python readers and consumers:

```text
LegacyOrbitLibrary.read_losvd_histograms()
dynamite.kinematics
dynamite.analysis
dynamite.plotter
Python NNLS weight solver
```

Expected Python shape is conceptually:

```text
(n_orbits, n_velocity_bins, n_spatial_bins)
```

Do not change axis order without changing every consumer.

## Population Output Contract

Fortran may write:

```text
datfil/orblib_pops.dat
datfil/orblibbox_pops.dat
```

Python reads these when `read_losvd_histograms(pops=True)` needs projected
population masses.

Population output is coupled to aperture mappings. A change to population
output requires tests that include population data, not only LOSVD-only
fixtures.

## Orbit-Class Output

Fortran writes:

```text
datfil/<root>.dat_orbclass.out
```

Python reads this text file through:

```text
LegacyOrbitLibrary.read_orbit_property_file()
```

This file is used for orbit classification/property analysis. Keep it in sync
with orbit counts in qgrid and LOSVD outputs.

## `interpolgrid`

The interpolation cache file:

```text
interpolgrid
```

is read and written by:

```text
orblib_fortran/source/potential/interpolated_potential.f90
```

It is not under `datfil/`; it is a bare path in the current working directory.
Python makes this model-local by running Fortran workers in the model
directory.

Do not assume `interpolgrid` is globally safe, hash-keyed, or automatically
invalidated.

## Files Not In The Active New-Format Contract

Old combined files such as:

```text
datfil/orblib.dat.bz2
datfil/orblibbox.dat.bz2
```

are legacy-format files. Python reader code still has compatibility branches,
but the active direct shared-library backend writes split qgrid/LOSVD/pops
files.

## Changing Output Safely

If any binary output record changes:

1. Update the Fortran writer.
2. Update Python readers in `dynamite/orblib.py`.
3. Update output docs in this file.
4. Regenerate or version fixtures.
5. Run fast API tests.
6. Run slow generated LOSVD parity tests.
7. Add population-output tests if the change touches `pops`.

Do not make a binary output change and rely only on import/unit tests.

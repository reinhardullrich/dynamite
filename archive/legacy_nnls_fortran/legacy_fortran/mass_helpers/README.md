# Legacy Mass-Helper Fortran Sources

These sources used to build the `triaxmass*` and `triaxmassbin*` executables.
They were only needed by the archived `LegacyWeightSolver`/NNLS workflow.

The active `orblib_fortran` backend no longer builds these programs. Current
orbit-library generation keeps only orbit-start and orbit-library integration
code active; Python-side NNLS uses Python-computed mass grids instead.

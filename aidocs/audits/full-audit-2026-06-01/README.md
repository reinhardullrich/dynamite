# Full Audit 2026-06-01

This folder contains the full local DYNAMITE audit run.

The audit is intentionally stored under `aidocs/`, not upstream `docs/`, so it
remains local AI/agent documentation for the personal fork.

## Audit Outputs

- `AUDIT_PLAN.md`: scope, boundaries, module split, and execution order.
- `00_environment.md`: local environment, dependency, compiler, and install
  findings.
- `01_build_packaging.md`: packaging, dependency, install, and CI findings.
- `02_configuration_runtime.md`: config parsing, settings, output setup,
  logging, and bootstrap findings.
- `03_physical_model_parameter_space.md`: system, component, parameter, and
  parameter-generator findings.
- `04_data_ingestion.md`: MGE, kinematics, populations, and data-prep findings.
- `05_model_state_iteration.md`: `all_models.ecsv`, model directory, resume,
  retry, and multiprocessing findings.
- `06_orbit_library_boundary.md`: Python-to-Fortran orbit-library handoff
  findings.
- `07_weight_solving.md`: legacy and Python NNLS solver findings.
- `08_legacy_fortran_backend.md`: Fortran build and numerical backend findings.
- `09_analysis_plotting_coloring.md`: analysis, plotting, and coloring
  findings.
- `10_tests_examples_docs.md`: development tests, examples, notebooks, docs,
  and CI coverage findings.
- `11_scientific_numerical_correctness.md`: cross-cutting scientific and
  numerical correctness findings.
- `12_operational_risk.md`: reproducibility, disk, destructive actions,
  concurrency, and local/global install risk findings.
- `13_galahad_runtime_check.md`: local GALAHAD build, link, and runtime solver
  checks after the initial audit gap was closed.
- `SUMMARY.md`: final prioritized findings and recommended next actions.

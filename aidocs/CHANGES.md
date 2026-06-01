# Change Log

This file is append-only. Add new entries at the bottom.

## 2026-06-01

- Created `aidocs/` for local AI/agent Markdown so upstream DYNAMITE `docs/`
  remains reserved for the project's Sphinx documentation.
- Copied `AGENTS.md` from the sibling CiFoS workspace and updated it to point
  at `aidocs/KNOWLEDGE.md` and `aidocs/CHANGES.md`.
- Moved local DYNAMITE review Markdown into `aidocs/`, including overview,
  code map, and audit files.
- Recorded that CiFoS work lives in the sibling
  `/home/reinhard/projects/thomas/cifos` folder.
- Added `aidocs/README.md` as the local AI documentation index.
- Added `aidocs/TECHNICAL_DOCUMENTATION.md` with detailed internal documentation of
  the DYNAMITE repository layout, config lifecycle, runtime object model,
  model iteration, orbit-library generation, weight solving, output state,
  failure recovery, and safe modification boundaries.
- Updated `aidocs/KNOWLEDGE.md` to reference the technical documentation.
- Created `aidocs/audits/full-audit-2026-06-01/` and recorded the full audit
  split, write boundaries, local-only install rule, execution order, and
  finding format.
- Documented the local install rule in `aidocs/KNOWLEDGE.md`: Python
  dependencies must go into `.venv/`, and any global/system install requires
  explicit approval first.
- Completed the 2026-06-01 full audit documentation under
  `aidocs/audits/full-audit-2026-06-01/`, including Fortran backend,
  analysis/plotting/coloring, tests/docs, scientific correctness, operational
  risk, and the prioritized `SUMMARY.md`.
- Recorded the completed local audit environment in `aidocs/KNOWLEDGE.md`,
  including `.venv/`, successful `pip check`, successful no-GALAHAD Fortran
  build, and the local `MPLCONFIGDIR` recommendation.
- Double-checked the completed full-audit documentation, reverified the main
  high-priority findings against the current source, reran `pip check` and
  pytest collection, and corrected stale wording about GALAHAD targets and the
  no-GALAHAD Fortran build note.
- Closed the GALAHAD audit gap: installed local GALAHAD 2.3 QP support from
  vendored dependency trees, repaired generated static archives missing
  `gltr.o` and `hsl_ma57d.o`, completed full GALAHAD-backed `make all`, ran
  link/load checks, and documented the results in
  `aidocs/audits/full-audit-2026-06-01/13_galahad_runtime_check.md`.
- Confirmed by runtime probe that solver-mode `5` reaches GALAHAD/QPB in both
  `triaxnnls_noCRcut` and `triaxnnls_CRcut`, but both logged
  `QPB_solve exit status = -5` while the shell process exited `0` and wrote
  output files.

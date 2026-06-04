# 12 Operational Risk Audit

Audit date: 2026-06-04

## Current Local State

- Work is on `Fortran-cleanup`.
- The working tree is intentionally dirty with current code/test/doc changes
  and this audit.
- Python dependencies are local in `.venv/`.
- Active Fortran build output is ignored under `orblib_fortran/build/`.

## Findings

### OR-001 - Dependency environment is local but not locked

Severity: Medium.

Recommendation: add a lock/snapshot for reproducible audits and benchmarks.

### OR-002 - Destructive operations remain easy to trigger

Severity: High.

Output reset, model cleanup, weight cleanup, plot cleanup, and all-models
cleanup all remove files or directories. Some can happen during construction or
repair flows.

Recommendation: add dry-run plans, confirmations for human scripts, and
trash/quarantine modes for large deletes.

### OR-003 - Model/cache writes are not atomic

Severity: High.

Direct final-path writes remain common for ECSV, NPZ, YAML, and weight files.

Recommendation: standardize temp-write plus `os.replace()`.

### OR-004 - Long-running jobs need structured timing and failure manifests

Severity: Medium/High.

DYNAMITE runs can take days/weeks. Logs alone are not enough to resume or
diagnose correctness/performance.

Recommendation: write per-model manifests with phase timings, file hashes,
backend versions, warning counts, and failure status.

### OR-005 - Local build products are safe but should not be mistaken for source

`orblib_fortran/build/`, caches, `.pytest_cache/`, and `__pycache__/` are
generated. Do not audit them as source.

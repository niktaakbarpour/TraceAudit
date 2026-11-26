# Source provenance and reuse record

The repository was assembled from the following TraceAudit-specific Hestia workspaces. The original workspaces were inspected read-only and left unchanged. Only source code, schemas, and explicitly synthetic test fixtures were copied. Dataset payloads, annotations, result rows, manifests containing episode IDs, videos, HDF5 files, transfer state, and outcome-bearing artifacts were excluded.

| Repository material | Source workspace | Imported content and adaptation |
|---|---|---|
| `research/source-snapshots/schema-v1.1/` | `traceaudit-structured-schema-v1.1-20261115` | Versioned event/outcome JSON Schemas only. |
| `research/source-snapshots/schema-v1.2/` | `traceaudit-structured-schema-v1.2-20261115` | Versioned event JSON Schema only. |
| `src/traceaudit/llm_infra.py`, `src/traceaudit/schemas/`, and `tests/` | `traceaudit-llm-infrastructure-v0.1-20261116` | Provider-neutral contract, schemas, tests, and synthetic fixtures. The installable copy changes only schema lookup and package imports; research behavior and fail-closed gating are unchanged. |

The event pilot and full-corpus runner were inspected but not imported. The pilot extractor source contains a fixed episode selection with outcome strata, and the full-corpus runner contains site-specific paths and depends on private catalog/archive state. Those files are not necessary to distribute the currently self-contained verification infrastructure. Their validated aggregate results are summarized without episode IDs or per-episode records in `docs/research-status.md`.

The schema validator scripts and their original tests were also excluded because they embed private absolute Hestia paths or episode identifiers. Their schema documents are retained; their validation outcomes are cited from saved aggregate reports rather than redistributed scripts.

No source from the separate ISSTA VLA failure-analysis or Trustworthy AI projects was imported. No candidate codebook package or human-review records are redistributed. The C01 pilot is summarized only at aggregate level in status documentation.

The inspected source files did not provide a complete component-level collaborator/license record. This repository therefore preserves source paths and versions but does not assert sole authorship of every inherited component. Confirm collaborator attribution and reuse rights with project records before making the repository public. No license is included pending the author's choice.

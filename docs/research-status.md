# Audit and research status

This status reflects the latest inspected TraceAudit workspaces on Hestia and the local workspaces available during the repository audit. Counts are tied to the artifacts named below, not generalized to unaudited episodes.

## Verified counts

| Scope | Verified count | Source |
|---|---:|---|
| Source catalog | 4,000 episodes; 80 task conditions | `traceaudit-full-corpus-v1-20261115/COMPLETION_REPORT.md`, `evaluation_only/cohort_counts_summary.json` |
| Catalog outcomes | 3,827 success; 173 failure | Same; outcome-derived counts remain evaluation-only in working datasets. |
| Fully validated and extracted | 2,040 episodes | `validation_results.json`; HDF5 hashes and 4,080 video hashes verified, 4,080 videos decoded and frame-aligned. |
| v1.2 events | 17,731 total | 8,717 gripper-command runs; 4,851 end-effector motion segments; 4,163 tracked-entity position changes. |
| Full-corpus event measurement recomputation | 17,731 passed | `validation_results.json`; frozen extraction criteria. |
| Event audit sample | 10 episodes, 145 non-terminal events | `traceaudit-event-audit-v1-20261115/AUDIT_REPORT.md`; all 145 deterministically recomputed and visually reviewed in both views. |
| Reference sample | 50 fixed IDs; 25 validated, 25 unavailable | `COMPLETION_REPORT.md`; unavailable Combined members were not replaced. |
| LLM experiments | 0 real calls; 0 real episode inputs | `traceaudit-llm-infrastructure-v0.1-20261116/validation_results.json`. |
| Human reference labels | 0 full-reference labels | Same validation artifact. The separate 10-case C01 agreement pilot is limited and does not establish broader category validity. |

The 34,180 event count previously mentioned in project history was not corroborated by the latest authoritative full-corpus validation artifact. The verified current output count is 17,731 for 2,040 processed episodes.

## Stage assessment

| Component | State | Notes |
|---|---|---|
| Catalog accounting | Complete | 4,000 unique records and outcome counts verified; all 4,000 execution payloads are not validated. |
| Extraction and schemas | Partial at corpus scale | 2,040 pass; 1,960 Combined payloads unavailable in owned local roots. The Combined transfer/staging package explicitly says transfer has not started and has pending authorization/routing conditions. |
| Event semantics | Audited within scope | Audit supports extraction relative to frozen numeric criteria, not completeness of all meaningful events or physical-cause labels. Simulator time values remain unverified. |
| Codebook | Under development | No general failure category set is frozen in the v0.3 decision. The local v0.4 record says C01 endpoint-relation wording is frozen; other tags remain observable signals or candidate constructs. `NO_FAILURE` remains unavailable without positive task-goal predicate evaluation. |
| Human reference | Pending | 50-ID sample incomplete and no full human labels. Annotation status must not be inferred from blank annotation packages or codebook development rosters. |
| LLM classification/explanations | Infrastructure only | Synthetic-tested contract, no provider integration, real queries, or episode-level predictions. |
| Event withholding | Infrastructure only | Single-event withholding implemented and synthetic-tested; eligibility rules and real-model response effects not evaluated. |
| Verification-budget comparison | Pending | No authoritative fixed budget or completed random/citation-guided/two-sided comparison was found. |
| Evaluation | Pending | No verified macro-F1, faithfulness, influential-event recall, human agreement, runtime, or cost results. |

## RQs and planned work

The audited Hestia TraceAudit markdown and workspace inventories did not surface an authoritative research proposal or current RQ1–RQ3 text. The three questions in the README are working formulations derived from the requested project methodology, not quotations or claims of approval. Confirm them against the approved proposal before freezing a study protocol.

The next research stages are completion of approved corpus access/validation, finalization of the classifier codebook and prompt, completion of the reference annotation protocol, implementation of eligibility and budget-allocation strategies, and then authorized real LLM experiments and evaluation. No stage should be represented as complete until its own validated artifact supports that claim.

# Public-release readiness review

Review date: 2026-11-26. The repository is private. This review separates content that is safe in the current private repository from checks still needed before any public release.

## Current repository content

- Contains TraceAudit provider-neutral LLM infrastructure, its schemas, synthetic fixtures/tests, aggregate project documentation, and selected JSON Schema documents.
- Does not contain raw recordings, HDF5 files, videos/images, model weights, episode-level predictions, manifests or identifiers, annotation forms, human labels, transfer state, or sealed reference records.
- Does not contain source from the separate ISSTA or Trustworthy AI projects.
- The package and its inherited components do not currently have a license file or a verified component-level collaborator/ownership record.

## Checks required before public release

1. **Code ownership and attribution:** Confirm the contributors and reuse rights for `traceaudit_llm_infra.py`, synthetic fixtures, and versioned schema material. The inspected package did not establish complete collaborator attribution. Add appropriate notices and contributor acknowledgment before public release.
2. **Project dataset and human-review governance:** Confirm that York University/project agreements permit public release of the aggregate corpus statistics and research description. No episode-level data or human-review records are included. Obtain a separate review before distributing any recordings, derived episode data, annotations, or labels.
3. **Benchmark terms and citations:** The official LIBERO repository states that its code is MIT-licensed and its datasets are CC BY 4.0. TraceAudit does not redistribute LIBERO benchmark data here; confirm the correct attribution and applicable terms for any future BDDL/task assets, images, or derived records before adding them. [LIBERO README](https://github.com/Lifelong-Robot-Learning/LIBERO/blob/master/README.md)
4. **Model terms:** OpenVLA-OFT's code repository provides an MIT license. The OpenVLA documentation separately warns that released pretrained model weights can inherit restrictions from their Llama-2 base. This repository contains no model weights or checkpoints; review the applicable checkpoint and base-model terms before redistributing any model-derived artifact. [OpenVLA-OFT license](https://github.com/moojink/openvla-oft/blob/main/LICENSE), [OpenVLA model licensing note](https://github.com/openvla/openvla#pretrained-vlas)
5. **Unpublished research/IP:** Confirm that public disclosure of the working research questions, pipeline description, aggregate counts, and ongoing methods is approved. The questions in the README are explicitly marked as working formulations because the audited workspace did not contain an authoritative RQ document.
6. **Final release scan:** Repeat secret, path/identifier, large-file, attribution, and human-data review against the exact release commit. Recheck `.gitignore` and the complete staged file list.

These are ownership, data-governance, attribution, and disclosure checks. The incomplete experiments described in `research-status.md` are scientific status limitations, not by themselves a reason that an accurately labeled ongoing project cannot be publicly documented.

## License options

No license has been selected. For original project code, **MIT** is a concise permissive option; **Apache-2.0** adds an express patent license and more detailed contributor/patent terms. Select only after ownership and collaborator attribution are clear. A code license would not grant rights to third-party benchmark data, project execution recordings, human annotations, model weights, or other excluded materials; those need their own terms and approvals.

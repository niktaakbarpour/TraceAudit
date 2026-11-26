# Reproducibility notes

- **Catalog and source manifests:** Versioned on approved research storage; not distributed here because they identify episode-level research data.
- **Schema and event versions:** v1.1 and v1.2 schemas and source validators are retained under `research/source-snapshots/` with their origin recorded in `docs/source-provenance.md`.
- **Extraction policy:** The full-corpus package used the existing thresholds `eef_step_m=0.001`, `eef_min_path_m=0.01`, `entity_step_m=0.002`, and `entity_min_net_m=0.01`; these values are reported as provenance, not a new configuration. Transition `j` maps to post-action frame `j+11` after ten settling actions. Source timestamps remain explicitly unverified.
- **Outcome separation:** Terminal outcomes are confined to evaluation-only outputs in the original pipeline; classifier and event-withholding inputs are outcome-blinded. No outcome-bearing records are included in this repository.
- **Randomness:** The 50-ID reference sample used the recorded fixed seed `traceaudit-reference-v1-20261114`; no episode IDs or sampled records are redistributed.
- **Synthetic tests:** The local package tests use only the small synthetic episode and response fixtures from the LLM infrastructure package. They require no data, cluster, GPU, or provider.
- **LLM accounting:** The existing infrastructure binds cache keys to request, provider/model, prompt, codebook, reference-lock, and generation settings. Provider token values are recorded only when supplied; missing counts remain unknown.
- **Research environment:** Hestia validation used a project environment with h5py, NumPy, jsonschema, Pillow, ffmpeg, and ffprobe. The archived Hestia runners depend on site-specific research paths and were not copied into this repository.

The saved Hestia artifacts report 3/3 corpus batch contract tests, 14/14 v1.1 tests, 10/10 v1.2 tests, and 15/15 synthetic LLM infrastructure tests passing. CI in this repository runs the isolated synthetic LLM contract suite only; it does not rerun corpus validation.

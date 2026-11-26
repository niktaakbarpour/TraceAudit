"""Run a small, fully synthetic TraceAudit contract demonstration."""

import json
from pathlib import Path

from traceaudit.llm_infra import build_input, ground_response, withhold_single_event


ROOT = Path(__file__).resolve().parents[1]
trace = json.loads((ROOT / "tests/fixtures/synthetic_episode.json").read_text())
response = json.loads(
    (ROOT / "tests/fixtures/synthetic_classifier_response.json").read_text()
)
request = build_input(trace, trace["task_instruction"])
grounding = ground_response(request, response)
perturbed = withhold_single_event(request, request["events"][0]["event_id"])

print(f"synthetic episode: {request['episode_id']}")
print(f"mechanically checked citations: {grounding['checked_citations']}")
print(f"events retained after withholding: {len(perturbed['events'])}")

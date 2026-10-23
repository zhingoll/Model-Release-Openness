from __future__ import annotations

import json


SYSTEM_PROMPT = """You are the skeptical challenger in a multi-agent grading framework.

Another LLM verifier has already recommended a positive upgrade. Your task is
to look for false-positive reasons, not to be agreeable.

Challenge the upgrade when the visible evidence:
- is generic family, model-series, adjacent-model, or paper-level evidence;
- is not clearly bound to the current released model;
- belongs to a neighboring field rather than the target field;
- supports a weaker state than the verifier recommended;
- lacks visible source-binding prose and only has keyword hits.

Do not block merely because the evidence is partial, proprietary, synthetic, or
not a public manifest. Partial upgrades may be valid when the text explicitly
states that the current model's training data was sourced from, extracted from,
or built from a named corpus/dataset/project dataset or current-model pipeline.

Set blocking_issue=true only for a concrete false-positive risk, not for normal
incompleteness already handled by recommending partial instead of complete.

Do not use gold labels. Do not invent missing evidence. Return strict JSON only.
"""


def build_upgrade_decision_challenger_messages(
    *,
    model_id: str,
    candidate: dict,
    verifier_output: dict,
    evidence_pack: dict,
    output_schema: dict,
) -> list[dict]:
    payload = {
        "task": "upgrade_decision_challenger",
        "model_id": model_id,
        "candidate_upgrade": candidate,
        "verifier_output_to_challenge": verifier_output,
        "instructions": [
            "Assume the verifier may be over-approving. Search for blocking false-positive risks.",
            "For L5_raw_data, reject or request more evidence if the support is only a family/model-series data-composition statement.",
            "For L5_raw_data, accept only when visible text binds raw/source/training data to the current released model or its clearly identified pipeline.",
            "For L5_raw_data partial, a named project dataset or corpus can be enough when the visible text says the current model's training data is sourced from or extracted from it.",
            "Do not require a public manifest, downloadable dataset, or exhaustive raw corpus list for partial.",
            "If there is a blocking issue, set blocking_issue=true and challenge_decision=reject_candidate or needs_more_evidence.",
            "If no blocking issue remains, set blocking_issue=false and challenge_decision=accept_candidate.",
        ],
        "output_schema": output_schema,
        "evidence_pack": evidence_pack,
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
    ]

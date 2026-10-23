from __future__ import annotations


CHALLENGE_DECISIONS = ["accept_candidate", "reject_candidate", "needs_more_evidence"]


def upgrade_decision_challenger_output_schema() -> dict:
    return {
        "type": "object",
        "required": [
            "challenge_decision",
            "blocking_issue",
            "confidence",
            "rationale",
            "blocking_risk_flags",
        ],
        "properties": {
            "challenge_decision": {"type": "string", "enum": CHALLENGE_DECISIONS},
            "blocking_issue": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string"},
            "blocking_risk_flags": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "current_model_not_bound",
                        "field_leakage",
                        "generic_family_or_paper_evidence",
                        "evidence_too_sparse",
                        "overclaimed_state",
                        "no_visible_source_binding",
                    ],
                },
            },
        },
    }

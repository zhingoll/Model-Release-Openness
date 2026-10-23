from __future__ import annotations


DECISION_ACTIONS = ["approve_upgrade", "reject_upgrade", "needs_more_evidence"]


def upgrade_decision_critic_output_schema() -> dict:
    return {
        "type": "object",
        "required": ["decision", "recommended_state", "confidence", "rationale", "risk_flags"],
        "properties": {
            "decision": {"type": "string", "enum": DECISION_ACTIONS},
            "recommended_state": {"type": "string", "enum": ["missing", "partial", "complete"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string"},
            "risk_flags": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "field_faithful_support_confirmed",
                        "current_missing_may_be_valid",
                        "candidate_overstates_evidence",
                        "complete_requires_stronger_evidence",
                        "partial_more_appropriate_than_complete",
                        "evidence_pack_too_sparse",
                        "neighboring_field_leakage",
                        "generic_family_or_infra_evidence",
                    ],
                },
            },
        },
    }

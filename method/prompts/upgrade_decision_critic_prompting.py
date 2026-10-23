from __future__ import annotations

import json


SYSTEM_PROMPT = """You are a second-stage positive-recall critic for a graded Agent framework.

Your task is not to grade the field from scratch. Your task is to review a
candidate upgrade proposed by a local undercall-recall verifier.

Approve the upgrade only when the evidence pack clearly shows field-faithful,
current-model-aligned support for a stronger state than the current prediction.

You may revise the proposed target. For example, if complete is overstated but
partial is supported, set decision=approve_upgrade and recommended_state=partial.

Reject the upgrade when:
- evidence is generic family/framework support rather than current-model support;
- evidence belongs to a neighboring field rather than the target field;
- the pack is too sparse to safely improve the current missing/partial state;
- the proposed complete state lacks the field-specific complete criteria.

Apply the field-specific criteria in the user payload. Do not require evidence
from a neighboring field: for example, L4_eval_code complete does not require
full dependency/environment details, and L4_eval_env complete does not require
full benchmark result tables.

Return strict JSON only.
"""


def _field_specific_criteria(field_id: str) -> dict:
    criteria = {
        "L3_train_code": {
            "complete": [
                "official or clearly current-model-aligned training source",
                "explicit training script, trainer implementation, or official training repository",
                "training command, launcher, recipe, or configuration tying the training procedure to the current model",
            ],
            "partial": [
                "current-model-grounded training script, command, trainer implementation, or training repository exists but coverage is incomplete",
                "official family-shared training artifact exists and is clearly aligned to this model family or release, not merely the same owner or a generic cookbook",
                "training implementation evidence is stronger than model-card process prose or hyperparameter/config text alone",
            ],
            "reject_or_flag_generic_family_or_infra_evidence": [
                "only model-card training_config, base_model, finetune metadata, or high-level training-process prose is present",
                "only inference, serving, kernel, optimization, deployment, or general framework repositories are present",
                "only owner-level family repositories or cookbook examples are present without clear current model-family/release alignment",
                "training scripts are for older/different model families and the pack does not show they apply to the current model",
            ],
            "do_not_require_for_complete": [
                "full hardware/environment setup",
                "full dataset license or raw data provenance",
            ],
        },
        "L3_train_env": {
            "complete": [
                "official or clearly current-model-aligned training source",
                "training-time framework stack or distributed training setup such as PyTorch, DeepSpeed, FSDP, Accelerate, Megatron, Lightning, or equivalent",
                "training-time runtime/dependency details such as CUDA, precision, optimizer/runtime libraries, FlashAttention, package stack, or equivalent",
                "hardware or compute setup such as GPU/TPU type, GPU count, node/cluster details, training time, or compute scale",
                "clear linkage to training rather than inference/demo/deployment",
            ],
            "partial": [
                "some training-environment evidence exists, such as framework or hardware, but not enough core criteria for complete",
                "environment evidence is current-model aligned but sparse, high-level, or mixed with non-training setup",
            ],
            "do_not_require_for_complete": [
                "full training code",
                "full data pipeline details",
                "exact package versions for every dependency",
            ],
        },
        "L4_eval_code": {
            "complete": [
                "official or clearly current-model-aligned evaluation source",
                "concrete evaluation entrypoint such as an eval script, benchmark launcher, module, or harness path",
                "runnable invocation or command tying the entrypoint to the current model or a documented benchmark task",
                "task/config reference such as benchmark YAML, task name, OpenCompass/VLMEval/lmms-eval task, or equivalent",
            ],
            "partial": [
                "evaluation repository, framework, or benchmark documentation exists but command/config linkage is incomplete",
                "script evidence is present but current-model linkage is indirect or only partially shown",
            ],
            "do_not_require_for_complete": [
                "full dependency list",
                "full hardware/environment setup",
                "all benchmark configurations",
                "benchmark score tables",
            ],
        },
        "L4_eval_env": {
            "complete": [
                "official or clearly current-model-aligned evaluation source",
                "evaluation-specific dependency or environment setup such as requirements, conda, docker, CUDA, or package versions",
                "configuration, hardware, or setup details tied to the evaluation workflow",
                "clear linkage to evaluation rather than inference/demo deployment",
            ],
            "partial": [
                "evaluation environment or dependency evidence exists but lacks enough setup/config detail",
                "environment evidence is partly mixed with inference setup but still tied to evaluation",
            ],
            "do_not_require_for_complete": [
                "full evaluation script contents",
                "benchmark score tables",
            ],
        },
        "L4_eval_data": {
            "complete": [
                "official or clearly current-model-aligned evaluation source",
                "named evaluation datasets or benchmark suite",
                "clear protocol/task linkage for how the model is evaluated on those datasets",
            ],
            "partial": [
                "named benchmarks are present but source/protocol linkage is incomplete",
            ],
        },
        "L4_no_overlap": {
            "complete": [
                "explicit contamination, decontamination, held-out, or train-test leakage protocol",
                "clear linkage to evaluation/test data rather than generic training data cleanup",
            ],
            "partial": [
                "overlap or contamination is mentioned but the protocol/linkage is incomplete",
            ],
        },
        "L5_data_prep": {
            "complete": [
                "official or clearly current-model-aligned preparation/preprocessing source",
                "concrete data preparation pipeline, script, recipe, or documented procedure",
                "clear linkage to preparing data for this model's training or evaluation workflow",
            ],
            "partial": [
                "current-model-aligned data preparation or preprocessing evidence exists but script/procedure linkage is incomplete",
                "repository or documentation shows relevant preparation steps, but the exact pipeline is sparse or indirect",
            ],
        },
        "L5_data_clean": {
            "complete": [
                "official or clearly current-model-aligned data cleaning/filtering source",
                "concrete cleaning, filtering, deduplication, quality-control, or safety filtering procedure",
                "clear linkage to the data used by the current model or its documented pipeline",
            ],
            "partial": [
                "cleaning/filtering evidence exists but is high-level, incomplete, or indirectly linked",
            ],
        },
        "L5_raw_data": {
            "complete": [
                "official or clearly current-model-aligned raw/source data disclosure",
                "named raw datasets, corpora, benchmark data, or source collection details",
                "clear linkage showing those data sources are used by the current model or its pipeline",
            ],
            "partial": [
                "named or described data sources exist but coverage, provenance, or linkage is incomplete",
                "repository/model card gives current-model-aligned source data hints but not a full raw-data disclosure",
            ],
            "reject_or_flag_generic_family_or_paper_evidence": [
                "paper or report discusses a broad model family but does not bind the described data to the current released model",
                "evidence only says training data, corpus, data mixture, or data composition without naming or describing usable source data",
                "evidence describes evaluation benchmarks, downstream tasks, or post-training data rather than raw/source data provenance",
                "evidence is from an adjacent model, previous generation, or same-owner family repository without explicit current-model linkage",
            ],
        },
        "L5_reproduce": {
            "complete": [
                "official or clearly current-model-aligned reproduction instructions",
                "actionable end-to-end steps, scripts, commands, or configuration for reproducing the data/model/evaluation workflow",
                "clear linkage to the current model rather than a generic framework demo",
            ],
            "partial": [
                "some reproduction steps, scripts, or configuration exist but the workflow is incomplete",
                "reproduction evidence is current-model aligned but relies on missing steps or external assumptions",
            ],
        },
    }
    return criteria.get(field_id, {})


def build_upgrade_decision_critic_messages(
    *,
    model_id: str,
    candidate: dict,
    evidence_pack: dict,
    output_schema: dict,
) -> list[dict]:
    payload = {
        "task": "upgrade_decision_critic",
        "model_id": model_id,
        "candidate_upgrade": candidate,
        "field_specific_criteria": _field_specific_criteria(str(candidate.get("field_id") or "")),
        "instructions": [
            "Review whether the proposed positive-recall upgrade should be applied.",
            "Approve only high-confidence under-call corrections.",
            "Set recommended_state to the safest field state supported by evidence.",
            "For complete, apply field_specific_criteria instead of generic completeness requirements.",
            "For L3_train_code missing->partial, require concrete training-code artifacts or clearly aligned family training artifacts; training_config or process prose alone is insufficient.",
            "When evidence is same-owner but not clearly current-model or current-family aligned, add generic_family_or_infra_evidence.",
            "For L5_raw_data, technical-report keywords alone are not enough; require visible current-model linkage and raw/source-data provenance, otherwise reject or request more evidence.",
            "Prefer needs_more_evidence over approve when the pack is too sparse.",
            "Do not use any gold labels or benchmark answers.",
        ],
        "output_schema": output_schema,
        "evidence_pack": evidence_pack,
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
    ]

# Measurement and Validation Guide

REMAP measures resource completeness and licensing freedom for each model
release. It collects public evidence, binds that evidence to a release and a
field, verifies the field judgment, and aggregates the judgments into an L/O
profile. The Verifier proposes field decisions. The Challenger checks
candidate positive upgrades for release binding, field relevance, and evidence
sufficiency before aggregation.

## Resource Rules

`method/resource_rules.csv` gives the complete, partial, and missing criteria
for all 19 resource fields. Eighteen fields determine the cumulative L1--L5
profile; `L4_no_overlap` is a separate diagnostic. At the primary threshold,
every required field through a stage must be complete. A release that does
not satisfy L1 is L0. The sensitivity analysis also computes the profile
when both complete and partial satisfy a required field.

Evidence must identify the target release and support the target field.
Related repositories and family reports qualify when their material is
explicitly applicable to that release. A self-explanatory command,
configuration, or recipe can provide training-description evidence. For
data cleaning, sampling must implement selection, exclusion, balancing, or
quality control; a mixture ratio alone is insufficient.

## Licensing Rules

`method/license_rules.csv` defines the model, code, and data checks. The
reviewed model terms determine the candidate category: O1 restrictive,
O2 reciprocal, O3 permissive, or O4 zero-obligation. The final profile retains
that category when the applicable code and data checks also qualify.
Component terms must be identified, release-bound, and resolved. Their
condition categories are recorded without reranking the model category.
Unresolved model terms or a failed applicable component check give
`Not qualified`.

The primary full-text rule accepts express coverage in the model terms or
qualifying component-specific terms. The separate-OSI sensitivity rule
changes the code check to require a separate, release-bound OSI-approved
license. The repository-default sensitivity rule gives explicit terms
priority and otherwise tests an unambiguous metadata license as coverage
for publisher-controlled, release-relevant artifacts in the target
Hugging Face repository. External repositories, external datasets,
third-party components, and artifacts with separate or conflicting terms
do not inherit that coverage.

Researchers reviewed the operative license texts and incorporated terms,
classified their permissions, and recorded their material scope,
obligations, and restrictions. `data/license_conditions.csv` links each
structured condition to its source URL and recorded clause locator.

## Independent Validation and Audit

Human86 contains 86 releases selected from the 845-release sample by
proportional stratification across L1--L5 and random selection within each
stratum. Its independent expert references evaluate REMAP predictions over
22 fields per release. The paired predictions and references reproduce
1,637 correct judgments out of 1,892, or 86.5%. The two anonymized rater
columns support the inter-rater agreement calculation. The constant
baseline predictions are provided for the comparison reported in the paper.

`method/data_license_audit_rules.csv` defines the six audit states. A
release-bound license found by manual review takes precedence, followed
by explicitly linked external access or terms that cannot be inspected.
The other states distinguish data disclosure, artifact availability, and
unresolved evidence.
The 144-case audit covers the 745 releases with missing or insufficient
data-license evidence. `data/data_license_audit.csv` retains both rater
states and the final state; `data/audit_explanations.csv` provides
author-prepared explanations for the 40 adjudicated disagreements.
These explanations summarize the retained adjudication records. They are
not quotations from the experts or new adjudications.

## Inference Settings

`method/inference_settings.json` records the paper settings: DeepSeek-R1
for resource and licensing assessment at temperature 0.1, Qwen3.5-Flash
for data processing at temperature 0, and GLM-5 for review at temperature
0.05. Offline reproduction reads the retained predictions and does not
make model API calls.

## MRBOM Example

`method/mrbom.schema.json` describes a release record containing its
resource judgments, licensing profile, and evidence links.
`method/mrbom.example.json` instantiates it for a release in the study.
Resource entries distinguish the 18 aggregation fields from the
no-overlap diagnostic. Each evidence link retains its support role.
License fields link to the applicable reviewed term set and component
decisions. Source metadata distinguishes a repository revision from a
content checksum and leaves unavailable observation times empty.

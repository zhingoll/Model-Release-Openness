# Annotation Reading Guide

This guide describes the study annotation procedure and the structured
records used to inspect its results. The field criteria are in
`method/resource_rules.csv` and `method/license_rules.csv`.

Two PhD students in software engineering independently annotated Human86.
For each assigned release, they inspected the Hugging Face page, model
card, file tree, linked repositories, papers, dataset pages, and official
documentation when available. Each release-field record contained a
label, reasoning, the material type and location, and supporting evidence.
Disagreements were adjudicated to establish the final reference labels.

The target release and target field define the evidence boundary. A
source must support both. Family-level material applies when it identifies
the target release or states that the relevant claim or artifact covers
that release. Resource fields use complete, partial, and missing according
to the field manual. The licensing fields record the model category and
the qualification of the applicable code and data terms. Unclear material
scope remains unresolved rather than being inferred from a platform tag.

The model identifier joins the released label records to the release
metadata. `data/human86_fields.csv` retains the two independent rater
labels, adjudicated reference, REMAP prediction, and baseline prediction
for each field. `L2_implementation` is the training-description field
called `L2_training` in the measurement data. `method/mrbom.example.json`
shows how resource labels, evidence links, repository versions, and
licensing decisions can be recorded for one study release; it is a
current reading example, not an expert submission.

For the separate data-license audit, `method/data_license_audit_rules.csv`
defines the six possible final states. `data/data_license_audit.csv`
contains the two rater states and the final classification for all 144
cases. Agreement retains the common label; disagreement is resolved by
adjudication using both evidence notes and further source review when
needed. The 40 adjudicated disagreements have author-prepared explanations
in `data/audit_explanations.csv`. The original expert records remain
unchanged in the private study archive.

# Data Dictionary

## Identifiers and Missing Values

`model_id` identifies a Hugging Face model release repository and is the join
key across release-level files. `item_id` has the same meaning in the weekly
candidate index. A model release is the measurement unit. `story_org` is the
publisher grouping used in the study; the namespace sensitivity check uses
the text before `/` in `model_id` instead.

An empty cell preserves an unrecorded or unresolved value in its source
record. `Not qualified` records a final licensing outcome. Keep unresolved
values separate from negative judgments when analyzing these records.

## Sample and Resource Measurements

`releases.csv` contains 845 formal releases, their resource and licensing
profiles, component license judgments, and publisher, region, and task
categories. `strict_level` is the cumulative resource level under the
complete-only threshold. `licensing_freedom_level` is the final license profile
after the applicable model, code, and data checks. `model_license_candidate`
records the reviewed model-license category before component qualification.

`weekly_candidates.csv` contains the preserved 1,660-entry candidate index.
It records the first and last observed qualifying week, number of qualifying
weeks, best weekly rank, and peak and mean weekly like increments within
the qualifying weeks. Formal-sample membership is defined by `releases.csv`.
The observation window is 3 March 2025 to 9 March 2026.

`resource_fields.csv` contains one label per release and resource field.
The labels are `complete`, `partial`, and `missing`. L1 covers deployment
materials, L2 covers model and training descriptions and reported results,
L3 covers training resources, L4 covers evaluation resources, and L5 covers
data preparation and reproduction resources. Cumulative aggregation requires
all included fields in each preceding stage to meet the threshold.
`L4_no_overlap` is a separate diagnostic and is excluded from this aggregation.
The field `L2_training` corresponds to `L2_implementation` in the Human86
exports; both identify the training-description field.

`sources.csv` records evidence identifiers, source URLs, and retained source
binding flags. Public source URLs omit access and sharing tokens as described
in `EVIDENCE.md`. `field_sources.csv` joins a resource field to an evidence
identifier within a release. `support_level` preserves the recorded support
role. `direct` and `strong` are primary-support candidates, `auxiliary`
records supporting context, and `disallowed` excludes that source for the
field. Field labels also depend on the field-specific sufficiency checks.
`release_versions.csv` adds the retained target-repository revision and
model-card checksum. `source_provenance.csv` records excerpt checksums and
source revisions where available. `EVIDENCE.md` explains their scope and
the meaning of unrecorded observation times.

## Human86

`human86_fields.csv` contains 1,892 rows: 86 releases times 22 fields.
`reference` is the final expert label, `prediction` is the REMAP output,
`rater_A` and `rater_B` are the independent rater labels, and
`constant_prediction` is the reported constant-baseline output. Inter-rater
agreement compares A with B. Test accuracy compares the prediction with the
final reference.

`human86_profiles.csv` contains the retained resource, licensing, and joint
profiles for these 86 releases. The prefixes `gold_` and `pred_` denote the
expert reference and REMAP prediction. `strict` uses the complete-only
threshold; `lenient` admits complete and partial labels. `constant_resource`
and `constant_licensing` are the aggregate baseline predictions.
The retained label `开放性不合格` means `Not qualified`. In a joint profile,
`L2+开放性不合格` denotes L2 with an unqualified license profile, whereas
`L2O3` denotes L2 with an O3 license profile.

Macro precision, recall, and F1 average over the union of observed reference
and predicted classes. A zero denominator contributes zero to a class metric.
Cohen's kappa uses the empirical marginal class proportions. License
qualification metrics treat O1--O4 as qualifying categories; the observed
qualified final profiles in this sample are O1 and O3.

## Licensing

`license_profiles.csv` maps each release to a canonical reviewed term set and
its component and final license judgments. `license_packages.csv` identifies
the 126 term sets, including 123 completed reviews and three unresolved sets.
`canonical_license_package_id` is the term-set key. It corresponds to
`license_text_id` in `license_dimensions.csv` and `license_conditions.csv`.

`license_dimensions.csv` contains the retained categorical coding of scope,
rights, obligations, and restrictions. `permitted_with_conditions` records a
conditional permission; `not_stated` records an unstated dimension;
`not_observed` records a condition not observed in the reviewed material.
`license_conditions.csv` contains condition identifiers, condition types,
affected materials, legal effects, and source URLs. Material names separated
by semicolons denote multiple affected materials. `evidence_locator`
preserves the recorded section or clause locator for the condition.

The completed-set analysis includes 2,698 condition records across 123 term
sets mapped to 842 releases. Counts of term sets and mapped releases use
different denominators. For a condition type, each term set and each mapped
release is counted once, even if the set contains multiple conditions of
that type. A release may be counted under several condition types.

`license_three_rules.csv` preserves the final profile under each scope rule:
`strict_separate_osi` is the separate-OSI sensitivity rule,
`explicit_full_text_primary` is the primary full-text scope analysis, and
`repository_default_lenient` is the repository-default sensitivity rule.
`separate_osi_code_qualified` records whether the code passes the separate,
release-bound OSI license check. The separate-OSI rule retains the primary
model and data judgments; only the code check changes.

## Audits and Sensitivity Analyses

`data_license_audit.csv` contains 144 final audited releases with both rater
labels and the final audit state. `data_license_population.csv` identifies
the 745 releases with missing or insufficient data-license evidence.
For each audit state, the weighted count is the sum of its within-stratum
audit proportions multiplied by the corresponding population counts.
Dividing this total by 745 gives the weighted proportion. Both datasets use
the resource levels in `releases.csv` for this calculation. Confidence
intervals use 10,000 within-stratum bootstrap resamples with seed 20260619.
`audit_sources.csv` contains the source URLs recorded for the audited cases.
`audit_explanations.csv` contains the final states, disagreement categories,
and author-prepared explanations for the 40 adjudicated disagreements.
These explanations are separate from the original expert wording.

`targeted_review.csv` records 30 release-field judgments. The `state` column
distinguishes decided and unresolved items; an unresolved item is not assigned
a replacement label. `retained_material_sensitivity.csv` contains the ten
reviewed units used for the retained-material substitution. The retained and
sensitivity statuses map `pass`, `uncertain`, and `fail` to `complete`,
`partial`, and `missing`, respectively.

`conditional_sensitivity.csv` records eight field substitutions under the
conditional reading of retained model-card evidence, with source revisions
and card hashes. These are analyst-defined sensitivity inputs, separate
from the primary labels and the expert test set. The combined scenario applies
the retained-material and conditional substitutions together.

Group summaries report release counts and within-group proportions.
Publisher-deletion analyses remove one publisher at a time and recompute
the community--company and China--USA contrasts. The namespace variant
repeats the calculation using the repository namespace as the grouping key.

# Reading the Evidence Records

Start with a release in `data/releases.csv`. Join its resource judgments in
`data/resource_fields.csv` to `data/field_sources.csv` by `model_id` and
field, then join to `data/sources.csv` by `model_id` and `evidence_id`.
Evidence identifiers are local to a release.

Public source URLs omit access and sharing tokens from query parameters.
The original URLs are retained in the private source records. A link that
requires such a token may not open directly from the public package; consult
the linked release repository for its publisher-provided access route.

## Repository Versions and Source Fingerprints

`data/release_versions.csv` records the Hugging Face repository revision
retained for each of the 845 releases, a revision-specific repository URL,
and the SHA-256 of the retained model-card string encoded as UTF-8. A
model-card checksum identifies that retained string, not a model weight
file or the entire repository. `repository_created_at` records creation
time and is separate from `observed_at`.

`data/source_provenance.csv` associates each source record with the
SHA-256 of its retained excerpt string and with a revision when it can
be established from the collected target repository metadata or a
commit-specific source URL. The target Hugging Face revision applies to
the target repository source only; it is not assigned to linked GitHub,
paper, dataset, or web sources. Empty revision and observation-time cells
mean those values were not recorded in the exported source metadata.
An excerpt checksum identifies retained content but does not provide
access to that content. Live pages may differ from the retained material.

## Binding and Support

The flags in `sources.csv` retain the recorded official-source and
target-release binding judgments. `support_level` in `field_sources.csv`
records how a source was treated for a particular field. A disallowed
source is not positive evidence. The final label is in
`resource_fields.csv`; counting links does not reconstruct that label.

For licensing, join `license_profiles.csv` to `license_packages.csv` by
`canonical_license_package_id`. The same key is called `license_text_id`
in the dimension and condition tables. `full_text_sha256` identifies the
retained license text. `evidence_locator` in the condition table preserves
the recorded clause or section locator. Empty locators remain empty.

## Audit Explanations

`data/audit_sources.csv` lists the URLs explicitly recorded in the
144-case data-license audit, including its target model pages. A source
URL identifies a recorded inspection location; it does not by itself
establish a qualifying data license. `audit_explanations.csv` explains
the 40 disagreement resolutions in English and retains their final
state and disagreement category. The original records are preserved
locally, with a private mapping to these author-prepared explanations.

Third-party documents and full excerpts are not redistributed in this
package. The source links, recorded versions, fingerprints, and structured
judgments support inspection without granting rights to those documents.

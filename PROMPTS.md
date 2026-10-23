# Preserved Prompt Templates

`method/prompts/` contains the preserved Verifier and Challenger template
pair, including the system instructions, user-message construction,
field-specific criteria, and response schemas. The implementation names
the positive-upgrade Verifier `critic`. It evaluates a proposed upgrade
against the evidence for the current release and field. The Challenger
receives the proposal, the Verifier response, and the evidence pack, then
returns acceptance, rejection, or a request for further evidence.

The four source files are preserved verbatim. `records.json` identifies
their roles and SHA-256 checksums. The private provenance audit connects
them to retained source versions and matching archived message arrays.
These are inspectable template records, not a complete archive of the
requests for all 845 releases. They do not include credentials, private
endpoints, or expert reference labels.

For field definitions, aggregation, license review, and inference settings,
read `METHOD.md` and the accompanying rule tables. The numerical replay
uses the retained final judgments. Inspecting these templates does not
require running an online prediction service.

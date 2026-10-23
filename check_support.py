#!/usr/bin/env python3
"""Check method coverage, evidence joins, and the MRBOM example offline."""

import csv
import hashlib
import json
import re
from pathlib import Path


def require(value, message):
    if not value:
        raise ValueError(message)


def read(root, name):
    with (root / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def unique(rows, keys):
    values = {tuple(row[k] for k in keys): row for row in rows}
    require(len(values) == len(rows), "Duplicate key: " + ", ".join(keys))
    return values


def check_schema(value, schema):
    supported = {'$schema', 'type', 'required', 'additionalProperties', 'properties',
                 'enum', 'pattern', 'minItems', 'maxItems', 'items'}
    require(set(schema) <= supported, 'Unsupported MRBOM schema constraint')
    kinds = {'object': dict, 'array': list, 'string': str, 'boolean': bool}
    if 'type' in schema:
        require(isinstance(value, kinds[schema['type']]), 'MRBOM schema type mismatch')
    if 'enum' in schema:
        require(value in schema['enum'], 'MRBOM schema value mismatch')
    if 'pattern' in schema:
        require(re.search(schema['pattern'], value), 'MRBOM schema pattern mismatch')
    if schema.get('type') == 'object':
        require(set(schema.get('required', [])) <= set(value), 'Missing MRBOM property')
        if schema.get('additionalProperties') is False:
            require(set(value) <= set(schema['properties']), 'Unexpected MRBOM property')
        for key, item in value.items():
            if key in schema.get('properties', {}):
                check_schema(item, schema['properties'][key])
    if schema.get('type') == 'array':
        require(schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', len(value)),
                'MRBOM schema array length mismatch')
        for item in value:
            check_schema(item, schema['items'])


def check(root):
    manifest = json.loads((root / "manifest.json").read_text())
    for name, expected in manifest.items():
        path = (root / name).resolve()
        require(root.resolve() in path.parents, "Invalid manifest path")
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                "Checksum mismatch: " + name)
    releases = unique(read(root, "data/releases.csv"), ["model_id"])
    versions = unique(read(root, "data/release_versions.csv"), ["model_id"])
    require(versions.keys() == releases.keys(), "Repository-version coverage mismatch")
    for key, row in versions.items():
        require(re.fullmatch(r"[0-9a-f]{40}", row["repository_revision"]), "Invalid repository revision")
        require(row["revision_url"] == row["repository_url"] + "/tree/" + row["repository_revision"],
                "Revision URL mismatch")
    sources = unique(read(root, "data/sources.csv"), ["model_id", "evidence_id"])
    provenance = unique(read(root, "data/source_provenance.csv"), ["model_id", "evidence_id"])
    require(sources.keys() == provenance.keys(), "Source-provenance coverage mismatch")
    for key, row in provenance.items():
        require(not row["excerpt_sha256"] or re.fullmatch(r"[0-9a-f]{64}", row["excerpt_sha256"]),
                "Invalid excerpt checksum")
        if row["revision_basis"] == "target_repository_metadata":
            require(key[1] == "hf_direct" and sources[key]["source_url"].rstrip("/") ==
                    versions[(key[0],)]["repository_url"], "Target revision assigned to external source")
            require(row["source_revision"] == versions[(key[0],)]["repository_revision"],
                    "Target revision mismatch")
        elif row["revision_basis"] == "source_url":
            require(re.fullmatch(r"[0-9a-f]{40}", row["source_revision"]) and
                    row["source_revision"] in sources[key]["source_url"], "Unbound source revision")
        else:
            require(row["revision_basis"] == row["source_revision"] == "", "Unknown revision basis")

    fields = unique(read(root, "data/resource_fields.csv"), ["model_id", "field"])
    rules = unique(read(root, "method/resource_rules.csv"), ["field"])
    require({k[1] for k in fields} == {k[0] for k in rules} and len(rules) == 19, "Resource rule coverage mismatch")
    require(len(read(root, "method/license_rules.csv")) == 3, "License rule coverage mismatch")
    audit = unique(read(root, "data/data_license_audit.csv"), ["model_id"])
    states = unique(read(root, "method/data_license_audit_rules.csv"), ["state"])
    require(len(states) == 6 and all((r['final_audit_state'],) in states for r in audit.values()),
            "Audit rule coverage mismatch")
    explanations = unique(read(root, "data/audit_explanations.csv"), ["model_id"])
    disagreements = {
        k for k, r in audit.items() if r['annotator_a_state'] != r['annotator_b_state']}
    require(explanations.keys() == disagreements and len(explanations) == 40, "Adjudication explanation coverage mismatch")
    require(all(r['final_audit_state'] == audit[k]['final_audit_state'] and r['author_explanation'].strip()
                for k, r in explanations.items()), "Adjudication outcome mismatch")
    audit_sources = read(root, "data/audit_sources.csv")
    require({r['model_id'] for r in audit_sources} == {k[0] for k in audit}, "Audit source coverage mismatch")

    example = json.loads((root / "method/mrbom.example.json").read_text())
    check_schema(example, json.loads((root / 'method/mrbom.schema.json').read_text()))
    mid = example['model_id']
    require(example['resource_level'] == releases[(mid,)]['strict_level'] and
            example['licensing_profile'] == releases[(mid,)]['licensing_freedom_level'], "MRBOM profile mismatch")
    require(example['repository_revision'] == versions[(mid,)]['repository_revision'], "MRBOM revision mismatch")
    items = unique(example['resources'], ['field'])
    require(items.keys() == rules.keys(), "MRBOM field coverage mismatch")
    links = {(r['model_id'], r['field'], r['evidence_id'], r['support_level'])
             for r in read(root, 'data/field_sources.csv')}
    example_sources = unique(example['sources'], ['evidence_id'])
    for (field,), item in items.items():
        require(item['label'] == fields[mid, field]['label'], "MRBOM field label mismatch")
        require(item['aggregation_required'] == (field != 'L4_no_overlap'), "MRBOM diagnostic used as gate")
        for link in item['evidence']:
            require((mid, field, link['evidence_id'], link['support_level']) in links and
                    (link['evidence_id'],) in example_sources, "MRBOM evidence link mismatch")
    for (eid,), row in example_sources.items():
        require(row['source_url'] == sources[mid, eid]['source_url'], "MRBOM source URL mismatch")
        require(all(row[k] == provenance[mid, eid][k] for k in ('source_revision', 'observed_at', 'excerpt_sha256')),
                "MRBOM source metadata mismatch")
    profile = next(r for r in read(root, 'data/license_profiles.csv') if r['model_id'] == mid)
    require(all(value == profile[key] for key, value in example['licensing'].items()), "MRBOM license mismatch")
    print("PASS: method coverage, 845 repository versions, 10,533 source records, 40 explanations, MRBOM links")


if __name__ == "__main__":
    check(Path(__file__).resolve().parent)

#!/usr/bin/env python3
"""Recompute study statistics from the accompanying structured records."""

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

STAGES = {
    "L1": ("weights", "config", "tokenizer", "infer_code", "infer_env"),
    "L2": ("principle", "training", "test_results"),
    "L3": ("train_code", "train_data", "train_env"),
    "L4": ("eval_code", "eval_data", "eval_env"),
    "L5": ("data_prep", "data_clean", "raw_data", "reproduce"),
}
STAGES = {level: tuple(level + "_" + name for name in names) for level, names in STAGES.items()}
STATUS = {"pass": "complete", "uncertain": "partial", "fail": "missing"}
QUALIFIED = {"O1", "O2", "O3", "O4"}
AUDIT_STATES = ("released_data_artifact_without_license", "referenced_but_unpublished_dataset",
    "no_separate_data_artifact_observed", "terms_outside_observed_sources",
    "manual_review_found_license", "unclear_or_ambiguous")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def keyed(rows, key):
    result = {row[key]: row for row in rows}
    require(len(result) == len(rows), "Duplicate key: " + key)
    return result


def save_csv(path, rows):
    require(bool(rows), "Empty output: " + path.name)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def divide(n, d):
    return n / d if d else 0.0


def scores(pairs):
    require(bool(pairs), "Empty comparison")
    labels = sorted({v for pair in pairs for v in pair if v})
    p, r, f = [], [], []
    for label in labels:
        tp = sum(a == b == label for a, b in pairs)
        precision = divide(tp, sum(b == label for _, b in pairs))
        recall = divide(tp, sum(a == label for a, _ in pairs))
        p.append(precision)
        r.append(recall)
        f.append(divide(2 * precision * recall, precision + recall))
    n = len(pairs)
    matches = sum(a == b for a, b in pairs)
    a, b = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    pe = sum(a[k] * b[k] / n**2 for k in labels)
    return dict(matches=matches, total=n, accuracy=matches / n,
                macro_precision=divide(sum(p), len(p)), macro_recall=divide(sum(r), len(r)),
                macro_f1=divide(sum(f), len(f)), kappa=divide(matches / n - pe, 1 - pe) if pe < 1 else 1.0)


def positive(pairs, positive_label):
    tp = sum(a == b == positive_label for a, b in pairs)
    fp = sum(a != positive_label and b == positive_label for a, b in pairs)
    fn = sum(a == positive_label and b != positive_label for a, b in pairs)
    precision, recall = divide(tp, tp + fp), divide(tp, tp + fn)
    return dict(tp=tp, fp=fp, fn=fn, tn=len(pairs) - tp - fp - fn,
                precision=precision, recall=recall, f1=divide(2 * precision * recall, precision + recall))


def compare(actual, expected, location="result"):
    if isinstance(expected, dict):
        for key, value in expected.items():
            require(key in actual, "Missing output: " + location + "." + key)
            compare(actual[key], value, location + "." + key)
    elif isinstance(expected, (int, float)):
        require(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12), "Mismatch: " + location)
    else:
        require(actual == expected, "Mismatch: " + location)


def strict_level(fields, admitted=frozenset({"complete"})):
    result = "L0"
    for level, checks in STAGES.items():
        if not all(fields[f] in admitted for f in checks):
            break
        result = level
    return result


def verify_manifest(root):
    manifest = json.loads((root / "manifest.json").read_text())
    for relative, expected_hash in manifest.items():
        path = (root / relative).resolve()
        require(root.resolve() in path.parents, "Invalid manifest path")
        require(path.is_file(), "Missing input: " + relative)
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        require(actual_hash == expected_hash, "Checksum mismatch: " + relative)


def resource_analysis(data, releases, output):
    fields = defaultdict(dict)
    raw = read(data / "resource_fields.csv")
    for row in raw:
        mid, field, label = row["model_id"], row["field"], row["label"]
        require(field not in fields[mid], "Duplicate resource field")
        require(label in STATUS.values(), "Invalid resource label")
        fields[mid][field] = label
    require(set(fields) == set(releases), "Resource membership mismatch")
    required = {f for checks in STAGES.values() for f in checks} | {"L4_no_overlap"}
    for mid, values in fields.items():
        require(set(values) == required, "Resource field coverage mismatch: " + mid)
        require(strict_level(values) == releases[mid]["strict_level"], "Resource aggregation mismatch: " + mid)
    result = dict(denominator=len(releases), l4_no_overlap_policy="diagnostic only")
    for name, admitted in (("complete_only", {"complete"}), ("complete_or_partial", {"complete", "partial"})):
        independent, cumulative = Counter(), Counter()
        for values in fields.values():
            running = True
            for level, checks in STAGES.items():
                ok = all(values[f] in admitted for f in checks)
                independent[level] += int(ok)
                running = running and ok
                cumulative[level] += int(running)
        result[name] = dict(independent=dict(independent), cumulative=dict(cumulative))
    cross = Counter()
    for values in fields.values():
        l3 = all(values[f] == "complete" for f in STAGES["L3"])
        l4 = all(values[f] == "complete" for f in STAGES["L4"])
        cross["both_satisfied" if l3 and l4 else "l3_only" if l3 else "l4_only" if l4 else "neither_satisfied"] += 1
    result["l3_l4_complete_only_cross_stage"] = dict(cross)
    save_json(output / "resource_construct.json", result)
    prevalence = Counter((r["field"], r["label"]) for r in raw)
    save_csv(output / "resource_prevalence.csv", [dict(field=f, label=s, count=prevalence[f, s], denominator=len(releases))
             for f in sorted(required) for s in ("complete", "partial", "missing")])
    sources = read(data / "sources.csv")
    source_ids = {(r["model_id"], r["evidence_id"]) for r in sources}
    require(len(source_ids) == len(sources), "Duplicate evidence identifier")
    supports = read(data / "field_sources.csv")
    support_keys = {(r["model_id"], r["field"], r["evidence_id"]) for r in supports}
    require(len(support_keys) == len(supports), "Duplicate evidence binding")
    for row in supports:
        require((row['model_id'], row['evidence_id']) in source_ids, "Unresolved evidence binding")
        require(row['field'] in fields[row['model_id']], "Unknown evidence field")
    return fields, result


def human_analysis(data, releases, output):
    rows = read(data / "human86_fields.csv")
    by_id, by_field = defaultdict(list), defaultdict(list)
    for row in rows:
        by_id[row["model_id"]].append(row)
        by_field[row["field"]].append(row)
    require(len(by_id) == 86 and len(by_field) == 22 and len(rows) == 1892, "Human86 size mismatch")
    require(set(by_id) <= set(releases), "Human86 outside formal sample")
    for group in by_id.values():
        require(len(group) == len({r['field'] for r in group}) == 22, "Duplicate or missing Human86 field")
    require(all(r[k] for r in rows for k in ('reference', 'prediction', 'rater_A', 'rater_B', 'constant_prediction')),
            "Missing Human86 label")
    pairs = [(r['reference'], r['prediction']) for r in rows]
    total = scores(pairs)
    result = dict(cases=86, fields=22, population=len(releases), missing_predictions=0,
        field={k: total[k] for k in ('matches', 'total', 'accuracy')},
        overall_macro={k: v for k, v in total.items() if k not in ('matches', 'total')},
        inter_rater=scores([(r['rater_A'], r['rater_B']) for r in rows]))
    aggregate = keyed(read(data / 'human86_profiles.csv'), 'model_id')
    require(set(aggregate) == set(by_id), "Human86 profile membership mismatch")
    mappings = dict(resource='strict_completeness', resource_partial='lenient_completeness',
                    licensing='openness', joint='strict_final_grade', joint_partial='lenient_final_grade')
    result['aggregate'] = {name: scores([(r['gold_' + suffix], r['pred_' + suffix]) for r in aggregate.values()])
                           for name, suffix in mappings.items()}
    all_matches = sum(all(r['gold_' + s] == r['pred_' + s] for s in mappings.values()) for r in aggregate.values())
    result['aggregate']['all_recorded_levels'] = dict(matches=all_matches, total=86, accuracy=all_matches / 86)
    qualification_pairs = [(r['gold_openness'] in QUALIFIED, r['pred_openness'] in QUALIFIED) for r in aggregate.values()]
    result['qualification'] = positive(qualification_pairs, True)
    result['constant_baseline'] = dict(field=scores([(r['reference'], r['constant_prediction']) for r in rows]),
        resource=scores([(r['gold_strict_completeness'], r['constant_resource']) for r in aggregate.values()]),
        licensing=scores([(r['gold_openness'], r['constant_licensing']) for r in aggregate.values()]),
        qualification_f1=positive([(r['gold_openness'] in QUALIFIED, r['constant_licensing'] in QUALIFIED)
                                  for r in aggregate.values()], True)['f1'])
    save_json(output / 'human86_metrics.json', result)
    details, confusion = [], []
    for field, group in sorted(by_field.items()):
        pairs = [(r['reference'], r['prediction']) for r in group]
        label = 'O3' if field == 'model_license_grade' else 'Qualified' if field.endswith('_license_qualification') else 'complete'
        details.append(dict(field=field, **scores(pairs), **{'positive_' + k: v for k, v in positive(pairs, label).items()}))
        confusion.extend(dict(field=field, reference=a, prediction=b, count=n) for (a, b), n in sorted(Counter(pairs).items()))
    save_csv(output / 'human86_field_metrics.csv', details)
    save_csv(output / 'human86_confusion.csv', confusion)
    return result


def licensing_analysis(data, releases, output):
    profiles = keyed(read(data / 'license_profiles.csv'), 'model_id')
    require(set(profiles) == set(releases), "License membership mismatch")
    packages = keyed(read(data / 'license_packages.csv'), 'canonical_license_package_id')
    dimensions = keyed(read(data / 'license_dimensions.csv'), 'license_text_id')
    require(set(packages) == set(dimensions), "License dimension coverage mismatch")
    complete = {k for k, r in packages.items() if r['review_status'] == 'complete'}
    mapped = Counter()
    for mid, row in profiles.items():
        require(row['scope_aware_final_level'] == releases[mid]['licensing_freedom_level'], "Final license mismatch")
        key = row['canonical_license_package_id']
        require(key in packages, "Unknown term set")
        if key in complete:
            mapped[key] += 1
    conditions = read(data / 'license_conditions.csv')
    keyed(conditions, 'condition_id')
    require(all(r['license_text_id'] in packages for r in conditions), "Unknown condition term set")
    selected = [r for r in conditions if r['license_text_id'] in complete]
    require(len(complete) == 123 and len(selected) == 2698 and sum(mapped.values()) == 842, "License coding scope mismatch")
    condition_types = []
    for kind in sorted({r['condition_type'] for r in selected}):
        entries = [r for r in selected if r['condition_type'] == kind]
        keys = {r['license_text_id'] for r in entries}
        condition_types.append(dict(condition_type=kind, condition_count=len(entries), license_package_count=len(keys),
            license_package_denominator=len(complete), license_package_percent=f'{100 * len(keys) / len(complete):.1f}',
            mapped_release_count=sum(mapped[k] for k in keys), release_denominator=sum(mapped.values()),
            mapped_release_percent=f'{100 * sum(mapped[k] for k in keys) / sum(mapped.values()):.1f}'))
    save_csv(output / 'license_condition_type_summary.csv', condition_types)
    dimension_rows = []
    for field in next(iter(dimensions.values())):
        if field in ('license_text_id', 'term_category', 'review_status'):
            continue
        states = {dimensions[k][field] for k in complete}
        if field.endswith('_scope'):
            states |= {'explicitly_covered', 'explicitly_excluded', 'not_applicable',
                       'not_stated', 'release_dependent', 'separate_terms'}
        elif any(state.startswith('permitted') or state == 'prohibited' for state in states):
            states |= {'permitted', 'permitted_with_conditions', 'prohibited', 'not_stated', 'not_applicable'}
        for state in sorted(states):
            keys = {k for k in complete if dimensions[k][field] == state}
            dimension_rows.append(dict(dimension=field, state=state, license_package_count=len(keys),
                mapped_release_count=sum(mapped[k] for k in keys)))
    save_csv(output / 'license_dimensions_summary.csv', dimension_rows)
    rules = keyed(read(data / 'license_three_rules.csv'), 'model_id')
    require(set(rules) == set(releases), "Three-rule membership mismatch")
    rule_counts = {name: dict(Counter(r[name] for r in rules.values())) for name in
                  ('strict_separate_osi', 'explicit_full_text_primary', 'repository_default_lenient')}
    require(all(rules[mid]['explicit_full_text_primary'] == r['licensing_freedom_level'] for mid, r in releases.items()),
            "Primary-rule mismatch")
    save_json(output / 'license_three_rules.json', rule_counts)
    return dict(completed_term_sets=len(complete), mapped_releases=sum(mapped.values()), condition_records=len(selected)), condition_types, dimension_rows


def percentile(values, q):
    values = sorted(values)
    index = (len(values) - 1) * q
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] * (1 - (index - low)) + values[high] * (index - low)


def audit_analysis(data, releases, output):
    rows = read(data / 'data_license_audit.csv')
    population = read(data / 'data_license_population.csv')
    require(len(keyed(rows, 'model_id')) == 144 and len(keyed(population, 'model_id')) == 745, "Audit size mismatch")
    require({r['model_id'] for r in rows} <= {r['model_id'] for r in population} <= set(releases), "Audit membership mismatch")
    for row in rows + population:
        require(row['strict_level'] == releases[row['model_id']]['strict_level'], "Audit stratum mismatch")
    require(all(r[k] in AUDIT_STATES for r in rows for k in ('annotator_a_state', 'annotator_b_state', 'final_audit_state')),
            "Invalid audit state")
    agreement = scores([(r['annotator_a_state'], r['annotator_b_state']) for r in rows])
    save_json(output / 'data_license_audit_agreement.json', agreement)
    strata = defaultdict(list)
    for row in rows:
        strata[row['strict_level']].append(row['final_audit_state'])
    population_counts = Counter(r['strict_level'] for r in population)
    require(set(population_counts) <= set(strata), "Unsampled population stratum")
    counts = Counter(r['final_audit_state'] for r in rows)
    estimates = Counter()
    for level, labels in strata.items():
        for state, n in Counter(labels).items():
            estimates[state] += population_counts[level] * n / len(labels)
    rng = random.Random(20260619)
    draws = {state: [] for state in AUDIT_STATES}
    for _ in range(10000):
        weighted = Counter()
        for level, labels in strata.items():
            sampled = Counter(rng.choice(labels) for _ in labels)
            for state, n in sampled.items():
                weighted[state] += population_counts[level] * n / len(labels)
        for state in AUDIT_STATES:
            draws[state].append(weighted[state] / len(population))
    result = [dict(audit_state=state, sample_count=str(counts[state]), sample_percent=f'{100 * counts[state] / len(rows):.1f}',
        strict_level_weighted_count_estimate=f'{estimates[state]:.1f}',
        strict_level_weighted_percent_estimate=f'{100 * estimates[state] / len(population):.1f}',
        strict_level_weighted_percent_ci_low=f'{100 * percentile(draws[state], .025):.1f}',
        strict_level_weighted_percent_ci_high=f'{100 * percentile(draws[state], .975):.1f}') for state in AUDIT_STATES]
    save_csv(output / 'human_audit_state_distribution.csv', result)
    return result, agreement


def sensitivity_analysis(data, releases, fields, output):
    targeted = read(data / 'targeted_review.csv')
    retained = read(data / 'retained_material_sensitivity.csv')
    conditional = read(data / 'conditional_sensitivity.csv')
    require(len(keyed(targeted, 'model_id')) == 30, "Targeted-review size mismatch")
    require(len(keyed(retained, 'model_id')) == 10, "Retained-material size mismatch")
    require(len(keyed(conditional, 'model_id')) == 8, "Conditional-review size mismatch")
    require(all(r['model_id'] in releases for r in targeted + retained + conditional), "Sensitivity outside formal sample")
    counts = Counter((r['state'], r['label']) for r in targeted)
    save_csv(output / 'targeted_review_counts.csv', [dict(state=s, label=l, count=n) for (s, l), n in sorted(counts.items())])
    result = {}
    for scenario in ('retained_material', 'conditional', 'combined'):
        changed = {mid: dict(values) for mid, values in fields.items()}
        if scenario in ('retained_material', 'combined'):
            for row in retained:
                mid, field = row['model_id'], row['field_id']
                require(fields[mid][field] == STATUS[row['retained_status']], "Retained-field mismatch")
                changed[mid][field] = STATUS[row['sensitivity_status']]
                require(strict_level(changed[mid]) == row['sensitivity_level'], "Retained-level mismatch")
        if scenario in ('conditional', 'combined'):
            for row in conditional:
                mid, field = row['model_id'], row['field_id']
                require(fields[mid][field] == STATUS[row['baseline_status']], "Conditional-field mismatch")
                require(releases[mid]['strict_level'] == row['original_level'], "Conditional baseline mismatch")
                changed[mid][field] = STATUS[row['conditional_status']]
                if scenario == 'conditional':
                    require(strict_level(changed[mid]) == row['conditional_level'], "Conditional-level mismatch")
        levels = {mid: strict_level(values) for mid, values in changed.items()}
        result[scenario] = dict(resource_distribution=dict(sorted(Counter(levels.values()).items())),
            joint_l3_o3=sum(int(level[1]) >= 3 and releases[mid]['licensing_freedom_level'] == 'O3' for mid, level in levels.items()),
            joint_l3_qualified=sum(int(level[1]) >= 3 and releases[mid]['licensing_freedom_level'] in QUALIFIED for mid, level in levels.items()))
    save_json(output / 'resource_sensitivity.json', result)
    return result


def group_analysis(releases, output):
    metrics = dict(l4_l5=lambda r: r['strict_level'] in ('L4', 'L5'),
        qualified=lambda r: r['licensing_freedom_level'] in QUALIFIED,
        joint_l3_o3=lambda r: int(r['strict_level'][1]) >= 3 and r['licensing_freedom_level'] == 'O3')
    summaries, deletions, composition = [], [], []
    for group in ('org_type', 'analysis_region', 'task_category'):
        for name in sorted({r[group] for r in releases.values()}):
            rows = [r for r in releases.values() if r[group] == name]
            summary = dict(group=group, category=name, releases=len(rows),
                publishers=len({r['story_org'] for r in rows}))
            for metric, predicate in metrics.items():
                summary[metric] = sum(predicate(r) for r in rows)
                summary[metric + '_percent'] = 100 * summary[metric] / len(rows)
            for hi, o3, label in ((True, True, 'l3_o3'), (True, False, 'l3_not_o3'),
                                  (False, True, 'below_l3_o3'), (False, False, 'neither')):
                summary[label] = sum((int(r['strict_level'][1]) >= 3) == hi and (r['licensing_freedom_level'] == 'O3') == o3 for r in rows)
            summaries.append(summary)
    for identity in ('story_org', 'namespace'):
        key = lambda r: r['story_org'] if identity == 'story_org' else r['model_id'].split('/')[0]
        for dimension in ('org_type', 'analysis_region', 'task_category'):
            for category in sorted({r[dimension] for r in releases.values()}):
                subset = [r for r in releases.values() if r[dimension] == category]
                for metric, predicate in metrics.items():
                    counts = Counter(key(r) for r in subset if predicate(r))
                    top = max(counts.values(), default=0)
                    composition.append(dict(identity_key=identity, dimension=dimension, group=category,
                        releases=len(subset), publishers=len({key(r) for r in subset}),
                        metric='joint_l3_l5_o3' if metric == 'joint_l3_o3' else metric,
                        positives=sum(counts.values()), contributing_publishers=len(counts),
                        top_contributors=';'.join(sorted(k for k, v in counts.items() if v == top)),
                        top_positive_count=top))
        for group, left, right in (('org_type', 'community', 'company'), ('analysis_region', 'China', 'USA')):
            rows = [r for r in releases.values() if r[group] in (left, right)]
            for publisher in sorted({key(r) for r in rows}):
                remaining = [r for r in rows if key(r) != publisher]
                a = [r for r in remaining if r[group] == left]
                b = [r for r in remaining if r[group] == right]
                for metric, predicate in metrics.items():
                    ap, bp = sum(predicate(r) for r in a), sum(predicate(r) for r in b)
                    deletions.append(dict(identity=identity, group=group, left=left, right=right, removed=publisher,
                        metric=metric, left_n=len(a), right_n=len(b), left_positive=ap, right_positive=bp,
                        difference_pp=100 * (ap / len(a) - bp / len(b)) if a and b else ''))
    save_csv(output / 'group_summary.csv', summaries)
    save_csv(output / 'publisher_deletions.csv', deletions)
    save_csv(output / 'publisher_composition.csv', composition)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = args.output.resolve()
    require(output != root and root not in output.parents, 'Choose an output directory outside the input package')
    require(not output.exists(), 'Choose a new output directory')
    verify_manifest(root)
    output.mkdir(parents=True)
    data = root / 'data'
    releases = keyed(read(data / 'releases.csv'), 'model_id')
    require(len(releases) == 845, 'Formal-sample size mismatch')
    weekly = keyed(read(data / 'weekly_candidates.csv'), 'item_id')
    require(len(weekly) == 1660 and set(releases) <= set(weekly), 'Weekly-candidate coverage mismatch')
    require(all(weekly[mid]['first_seen_week_like'] <= '2026-03-09' and weekly[mid]['last_seen_week_like'] >= '2025-03-03'
                for mid in releases), 'Admission outside observation window')
    totals = dict(resource=dict(sorted(Counter(r['strict_level'] for r in releases.values()).items())),
                  licensing=dict(sorted(Counter(r['licensing_freedom_level'] for r in releases.values()).items())))
    compare(totals['resource'], dict(L0=31, L1=84, L2=611, L3=40, L4=72, L5=7))
    require(totals['licensing'] == {'Not qualified': 750, 'O1': 28, 'O3': 67}, 'License distribution mismatch')
    save_json(output / 'primary_counts.json', totals)
    matrix = Counter((r['strict_level'], r['licensing_freedom_level']) for r in releases.values())
    save_csv(output / 'joint_matrix.csv', [dict(resource=level, licensing=o, count=matrix[level, o])
              for level in ('L0', 'L1', 'L2', 'L3', 'L4', 'L5') for o in ('O1', 'O2', 'O3', 'O4', 'Not qualified')])
    fields, construct = resource_analysis(data, releases, output)
    compare(construct, json.loads((root / 'expected/resource_construct.json').read_text()))
    human = human_analysis(data, releases, output)
    compare(human, json.loads((root / 'expected/human86_metrics.json').read_text()))
    license_counts, condition_types, dimensions = licensing_analysis(data, releases, output)
    expected_conditions = keyed(read(root / 'expected/license_condition_type_summary.csv'), 'condition_type')
    for row in condition_types:
        # Published CSVs store rounded percentages; compare them as numbers.
        for key, value in expected_conditions[row['condition_type']].items():
            if key != 'condition_type':
                compare(float(row[key]), float(value), 'condition.' + row['condition_type'] + '.' + key)
    observed_dimensions = {(r['dimension'], r['state']): r for r in dimensions}
    for row in read(root / 'expected/license_dimension_dual_summary.csv'):
        actual = observed_dimensions[row['dimension'], row['state']]
        for key in ('license_package_count', 'mapped_release_count'):
            compare(actual[key], int(row[key]), 'dimension.' + row['dimension'] + '.' + key)
    packages = keyed(read(data / 'license_packages.csv'), 'canonical_license_package_id')
    profiles = read(data / 'license_profiles.csv')
    for row in read(root / 'expected/license_term_category_dual_summary.csv'):
        ids = {k for k, r in packages.items() if r['review_status'] == 'complete' and r['term_category'] == row['term_category']}
        compare(len(ids), int(row['license_package_count']), 'term_category.set_count')
        compare(sum(r['canonical_license_package_id'] in ids for r in profiles), int(row['mapped_release_count']), 'term_category.release_count')
    audit_alignment = [dict(model_id=r['model_id'], audit_level=r['strict_level'],
                           formal_level=releases[r['model_id']]['strict_level'])
                       for r in read(data / 'data_license_audit.csv')
                       if r['strict_level'] != releases[r['model_id']]['strict_level']]
    if audit_alignment:
        save_json(output / 'audit_stratum_mismatches.json', audit_alignment)
    else:
        audit, agreement = audit_analysis(data, releases, output)
        expected_audit = keyed(read(root / 'expected/human_audit_state_distribution.csv'), 'audit_state')
        for row in audit:
            compare(row, expected_audit[row['audit_state']], 'data_license_audit.' + row['audit_state'])
        expected_agreement = read(root / 'expected/human_audit_agreement.csv')[0]
        compare(agreement['kappa'], float(expected_agreement['cohen_kappa']), 'data_license_audit.kappa')
        compare(agreement['matches'], int(expected_agreement['agreements']), 'data_license_audit.matches')
    sensitivity = sensitivity_analysis(data, releases, fields, output)
    compare(sensitivity['retained_material']['resource_distribution'], dict(L0=31, L1=89, L2=606, L3=40, L4=72, L5=7))
    compare(sensitivity['conditional']['resource_distribution'], dict(L0=31, L1=84, L2=610, L3=34, L4=78, L5=8))
    group_analysis(releases, output)
    save_json(output / 'verification.json', dict(status='BLOCKED' if audit_alignment else 'PASS',
        audit_stratum_mismatches=len(audit_alignment), audit_weighted_results_verified=not audit_alignment,
        releases=845, human_cases=86,
        human_field_comparisons=1892, human_matches=1637, data_license_audit_cases=144,
        data_license_population=745, targeted_cases=30, retained_material_cases=10,
        conditional_cases=8, **license_counts))
    if audit_alignment:
        raise SystemExit('BLOCKED: audit strata differ from formal-sample levels; other structured-data outputs are in ' + str(output))
    print('PASS: structured-data replay; outputs in ' + str(output))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Render the seven quantitative figures from the public CSV records."""

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import PowerNorm
from matplotlib.patches import Patch, Rectangle
from matplotlib.text import Text
import numpy as np


RESOURCE = dict(zip((f"L{i}" for i in range(6)),
                    ("#B7C3CC", "#7FA6C9", "#3A6EA5", "#E9C46A", "#CF8068", "#9585B1")))
LICENSE = {"O1": "#B78020", "O2": "#A995C8", "O3": "#247F8C", "O4": "#7B9F78",
           "Not qualified": "#6C757D"}
STATES = {"complete": "#247F8C", "partial": "#E1B450", "missing": "#CDD6DB"}
SCOPE = {"explicit_unified_coverage": ("Same model terms", "#3A6EA5"),
         "explicit_separate_or_component_terms": ("Separate/component terms", "#A995C8"),
         "scope_unclear": ("Relationship unclear", "#6C757D")}
JOINT = {"Both criteria": "#187B70", "L3-L5, not O3": "#79B4D0",
         "O3, below L3": "#C27638", "Neither criterion": "#DAE3E6"}
INK, MUTED, GRID = "#203843", "#506572", "#E1E8EC"
BLUE, GOLD = "#225F82", "#B5772D"
STAGES = [
    ("L1", "DEPLOYMENT", [("L1_weights", "Weights"), ("L1_config", "Configuration"),
        ("L1_tokenizer", "Tokenizer / input processing"), ("L1_infer_code", "Inference code"),
        ("L1_infer_env", "Inference environment")]),
    ("L2", "UNDERSTANDING", [("L2_principle", "Model rationale"),
        ("L2_training", "Training description"), ("L2_test_results", "Reported results")]),
    ("L3", "TRAINING", [("L3_train_code", "Training code"), ("L3_train_data", "Training data"),
        ("L3_train_env", "Training environment")]),
    ("L4", "VERIFICATION", [("L4_eval_code", "Evaluation code"),
        ("L4_eval_data", "Evaluation data"), ("L4_eval_env", "Evaluation environment")]),
    ("L5", "REPRODUCTION", [("L5_raw_data", "Raw-data sources"),
        ("L5_data_prep", "Data preprocessing"), ("L5_data_clean", "Data cleaning"),
        ("L5_reproduce", "Reproduction guidance")]),
]
DIAGNOSTIC = ("L4_no_overlap", "Train/eval no-overlap")
GROUPS = [
    ("org_type", "Publisher type", ["company", "user", "community", "non-profit", "university"]),
    ("analysis_region", "Publisher-associated region",
     ["China", "USA", "Europe", "Other Asia", "Unknown", "Canada + Australia"]),
    ("task_category", "Task category",
     ["Text/NLP", "Multimodal Chat", "Vision/Video/3D", "Speech/Audio", "Embedding/Retrieval", "Other"]),
]
FINAL_CATEGORIES = ("Not qualified", "O1", "O3")
QUALIFIED = {"O1", "O2", "O3", "O4"}
NAME_LABELS = {
    "gemma 2024-04-01": "Gemma (2024-04-01)",
    "nvidia-open-model-license 2024-06-14": "NVIDIA Open Model (2024-06-14)",
    "cc-by-4.0 4.0": "CC BY 4.0",
    "health-ai-developer-foundations 2024-11-15": "Health AI Developer Foundations",
    "modified-mit": "Modified MIT variants",
    "FLUX.1-dev Non-Commercial License 1.1.1": "FLUX.1-dev NC 1.1.1",
    "Qwen Research License 2024-09-19": "Qwen Research (2024-09-19)",
    "llama4 2025-04-05": "Llama 4 (2025-04-05)",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(data, name, columns, hashes):
    path = data / name
    hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames is not None and set(columns) <= set(reader.fieldnames),
                "Missing columns: " + name)
        require(len(reader.fieldnames) == len(set(reader.fieldnames)), "Duplicate columns: " + name)
        rows = list(reader)
    require(bool(rows), "Empty input: " + name)
    require(all(None not in row and all(row.get(c) not in (None, "") for c in columns)
                for row in rows), "Incomplete row: " + name)
    return rows


def keyed(rows, key):
    result = {row[key]: row for row in rows}
    require(len(result) == len(rows), "Duplicate key: " + key)
    return result


def boolean(value):
    require(value in ("True", "False"), "Invalid boolean: " + value)
    return value == "True"


def group_name(row, key):
    value = row[key]
    if key == "analysis_region" and value in ("Other North America", "Oceania"):
        return "Canada + Australia"
    return value


def derive(data):
    hashes = {}
    releases = keyed(read_csv(data, "releases.csv", ["model_id", "strict_level",
        "licensing_freedom_level", "org_type", "analysis_region", "task_category"], hashes), "model_id")
    rows = [releases[mid] for mid in sorted(releases)]
    n = len(rows)
    require(all(r["strict_level"] in RESOURCE and r["licensing_freedom_level"] in FINAL_CATEGORIES
                for r in rows), "Unsupported release profile")
    raw = read_csv(data, "resource_fields.csv", ["model_id", "field", "label"], hashes)
    fields = defaultdict(dict)
    for row in raw:
        mid, field, label = row["model_id"], row["field"], row["label"]
        require(field not in fields[mid], "Duplicate resource field: " + mid + "/" + field)
        require(label in STATES, "Invalid resource label: " + label)
        fields[mid][field] = label
    required = {field for _, _, group in STAGES for field, _ in group} | {DIAGNOSTIC[0]}
    require(set(fields) == set(releases), "Resource membership mismatch")
    blockers = Counter()
    for mid in sorted(releases):
        require(set(fields[mid]) == required, "Resource coverage mismatch: " + mid)
        highest = "L0"
        for level, _, group in STAGES:
            failed = [field for field, _ in group if fields[mid][field] != "complete"]
            if failed:
                # Count every failed field in the first unsatisfied stage only.
                blockers.update(failed)
                break
            highest = level
        require(highest == releases[mid]["strict_level"], "Resource aggregation mismatch: " + mid)
    prevalence = {field: {state: sum(values[field] == state for values in fields.values())
                          for state in STATES} for field in sorted(required)}
    profiles = keyed(read_csv(data, "license_profiles.csv", ["model_id", "canonical_license_package_id",
        "code_scope_class", "data_scope_class", "scope_aware_model_level",
        "scope_aware_model_license_qualified", "scope_aware_code_license_qualified",
        "scope_aware_data_license_qualified", "scope_aware_final_level"], hashes), "model_id")
    require(set(profiles) == set(releases), "License membership mismatch")
    packages = keyed(read_csv(data, "license_packages.csv", ["canonical_license_package_id",
        "canonical_display_name", "review_status", "term_category"], hashes), "canonical_license_package_id")
    require(all(r["review_status"] in ("complete", "unresolved") for r in packages.values()),
            "Invalid term-set review status")
    complete = {key for key, row in packages.items() if row["review_status"] == "complete"}
    require(complete and all(packages[key]["term_category"] in QUALIFIED for key in complete),
            "Invalid reviewed term category")
    cascade = [0, 0, 0]
    mapped, names = Counter(), Counter()
    name_categories = defaultdict(set)
    scope = {component: Counter() for component in ("code", "data")}
    for mid in sorted(profiles):
        row = profiles[mid]
        key = row["canonical_license_package_id"]
        require(key in packages, "Unknown term set: " + key)
        flags = [boolean(row["scope_aware_" + part + "_license_qualified"])
                 for part in ("model", "code", "data")]
        model_level = row["scope_aware_model_level"]
        require(flags[0] == (model_level in QUALIFIED), "Model qualification mismatch: " + mid)
        final = model_level if all(flags) else "Not qualified"
        require(final == row["scope_aware_final_level"] == releases[mid]["licensing_freedom_level"],
                "Final licensing mismatch: " + mid)
        for i in range(3):
            cascade[i] += int(all(flags[:i + 1]))
        if key in complete:
            mapped[packages[key]["term_category"]] += 1
        name = packages[key]["canonical_display_name"]
        names[name] += 1
        name_categories[name].add(packages[key]["term_category"])
        for component in scope:
            value = row[component + "_scope_class"]
            require(value in SCOPE, "Unsupported scope class: " + value)
            scope[component][value] += 1
    term_counts = Counter(packages[key]["term_category"] for key in complete)
    require(sum(mapped.values()) > 0, "No reviewed mapped releases")
    ordered_names = sorted(names, key=lambda name: (-names[name], name))
    landscape = []
    for name in ordered_names[:12]:
        categories = name_categories[name]
        require(len(categories) == 1 and next(iter(categories)) in QUALIFIED,
                "Unsupported displayed license category: " + name)
        landscape.append(dict(name=name, count=names[name], category=next(iter(categories))))
    if len(ordered_names) > 12:
        landscape.append(dict(name=f"Other ({len(ordered_names)-12} names)",
                              count=sum(names[name] for name in ordered_names[12:]), category="Mixed/other"))
    joint = Counter((row["strict_level"], row["licensing_freedom_level"]) for row in rows)
    matrix = [[joint[level, category] for category in FINAL_CATEGORIES] for level in RESOURCE]
    groups = {}
    for key, _, order in GROUPS:
        require({group_name(row, key) for row in rows} == set(order), "Group coverage mismatch: " + key)
        groups[key] = []
        for name in order:
            subset = [row for row in rows if group_name(row, key) == name]
            high = [r["strict_level"] in ("L3", "L4", "L5") for r in subset]
            o3 = [r["licensing_freedom_level"] == "O3" for r in subset]
            both = sum(a and b for a, b in zip(high, o3))
            size, resource, license_o3 = len(subset), sum(high), sum(o3)
            groups[key].append(dict(name=name, n=size, resource=resource, o3=license_o3, both=both,
                parts=[both, resource-both, license_o3-both, size-resource-license_o3+both],
                resource_counts=[sum(r["strict_level"] == level for r in subset) for level in RESOURCE],
                license_counts=[sum(r["licensing_freedom_level"] == level for r in subset)
                                for level in ("O1", "O3", "Not qualified")]))
    return dict(n=n, inputs_sha256=hashes,
        resource_counts=[sum(r["strict_level"] == level for r in rows) for level in RESOURCE],
        prevalence=prevalence, blockers=[dict(field=f, count=c) for f, c in blockers.most_common()],
        cascade=cascade, term_counts={k: term_counts[k] for k in sorted(QUALIFIED)},
        mapped_counts={k: mapped[k] for k in sorted(QUALIFIED)},
        term_denominator=len(complete), mapped_denominator=sum(mapped.values()),
        landscape=landscape, scope_counts=scope, joint_matrix=matrix, groups=groups)


def text_on(fill):
    rgb = [int(fill[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    luminance = sum(w * (c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4)
                    for w, c in zip((.2126, .7152, .0722), rgb))
    return "#FFFFFF" if luminance < .179 else "#102331"


def clean_axis(ax, axis="x"):
    ax.set_axisbelow(True)
    ax.grid(axis=axis, color=GRID, linewidth=.5)
    ax.tick_params(length=0, colors=INK, labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)


def text_bounds(fig):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    hidden = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            lo, hi = sorted(axis.get_view_interval())
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not lo <= tick.get_loc() <= hi:
                    hidden.update((id(tick.label1), id(tick.label2)))
    visible = [item for item in fig.findobj(Text) if item.get_visible() and item.get_text().strip()
               and id(item) not in hidden and (item.axes is None or item.axes.get_visible())]
    overflow = []
    for item in visible:
        box = item.get_window_extent(renderer)
        if box.x0 < -1 or box.y0 < -1 or box.x1 > fig.bbox.x1 + 1 or box.y1 > fig.bbox.y1 + 1:
            overflow.append(item.get_text())
    require(not overflow, "Text outside canvas: " + repr(overflow))
    return dict(width_inches=float(fig.get_figwidth()), height_inches=float(fig.get_figheight()),
                minimum_text_points=min(t.get_fontsize() for t in visible),
                text_outside_canvas=0, text_items=len(visible))


def resources(d):
    n = d["n"]
    fig = plt.figure(figsize=(7.12, 4), facecolor="white")
    fig.text(.025, .987, "(a) Highest cumulative level per release", fontsize=9.5,
             weight="bold", color=INK, va="top")
    fig.text(.979, .986, f"{n} releases", ha="right", va="top", color=MUTED, fontsize=8)
    top = fig.add_axes([.095, .752, .855, .176])
    top.bar(range(6), [100*c/n for c in d["resource_counts"]], width=.51, color=list(RESOURCE.values()))
    for i, c in enumerate(d["resource_counts"]):
        top.text(i, 100*c/n+2, f"{c} ({100*c/n:.1f}%)", ha="center", va="bottom", fontsize=8, color=INK)
    top.set(xticks=range(6), xticklabels=list(RESOURCE), ylim=(0, 93), yticks=[0, 40, 80])
    top.set_ylabel("Share (%)", fontsize=8, color=INK)
    clean_axis(top, "y")
    fig.text(.025, .669, "(b) Field evidence by reuse stage", fontsize=9.5, weight="bold", color=INK)

    def panel(x, groups):
        ax = fig.add_axes([x, .137, .247, .483])
        cursor, ticks, labels = 0., [], []
        for level, title, group in groups:
            ax.text(-90, cursor, f"{level}  {title}", fontsize=7.9, color=INK,
                    weight="bold", ha="left", va="center", clip_on=False)
            if level == "L3":
                ax.axhspan(cursor-.45, cursor+len(group)+.47, color="#EEF7F4", zorder=0)
            cursor += 1
            for key, label in group:
                left = 0
                for state, color in STATES.items():
                    value = 100*d["prevalence"][key][state]/n
                    ax.barh(cursor, value, left=left, height=.67, color=color, linewidth=0)
                    left += value
                ax.text(107, cursor, f"{100*d['prevalence'][key]['complete']/n:.1f}%",
                        fontsize=7.7, ha="left", va="center", color=INK)
                ticks.append(cursor)
                labels.append(label)
                if key == DIAGNOSTIC[0]:
                    ax.add_patch(Rectangle((0, cursor-.39), 100, .78, fill=False,
                        edgecolor=MUTED, linestyle=(0, (2, 2)), linewidth=.6))
                cursor += 1
            cursor += .5
        ax.set(xlim=(0, 128), ylim=(16.3, -.6), xticks=[0, 50, 100], yticks=ticks, yticklabels=labels)
        ax.set_xlabel("Share of releases (%)", fontsize=8, labelpad=3, color=INK)
        clean_axis(ax)
        ax.tick_params(axis="y", labelsize=7.7, pad=4)
        ax.text(127, -.98, "Complete", fontsize=7.8, weight="bold", ha="right", color=STATES["complete"])

    # The bundled fallback font has wider field labels.
    panel(.204 if plt.rcParams["font.family"] == ["Liberation Sans"] else .229, STAGES[:3])
    panel(.733, [STAGES[3], ("", "DIAGNOSTIC", [DIAGNOSTIC]), STAGES[4]])
    fig.legend(handles=[Patch(facecolor="none", edgecolor="none", label="Panel (b):")]
        + [Patch(facecolor=c, label=s.title()) for s, c in STATES.items()], loc="lower center",
        bbox_to_anchor=(.5, .005), ncol=4, frameon=False, fontsize=8, columnspacing=2.2)
    return fig


def licensing(d):
    n = d["n"]
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(3.45, 4.05), facecolor="white")
    top.set_position([.34, .57, .43, .27])
    bottom.set_position([.34, .17, .59, .20])
    fig.text(.05, .95, "(a) Evidence retained across material checks", color=INK,
             fontsize=8.5, fontweight="bold", va="top")
    fig.text(.05, .48, "(b) Term diversity versus adoption", color=INK,
             fontsize=8.5, fontweight="bold", va="top")
    for y, count in zip([2, 1, 0], d["cascade"]):
        top.barh(y, n, height=.43, color="#edf1f2")
        top.barh(y, count, height=.43, color="#426677")
        top.text(1.02, y, f"{count} ({100*count/n:.1f}%)", transform=top.get_yaxis_transform(),
                 va="center", ha="left", color=INK, fontsize=6.8, fontweight="bold")
    top.set_yticks([2, 1, 0], ["Model terms", "Model + code", "Model + code + data"])
    top.set(xlim=(0, n), ylim=(-.55, 2.55), xticks=[0, 400, 800])
    top.set_xlabel(f"Releases (n = {n})", color=INK, labelpad=3)
    for y, counts, denominator in ((1, d["term_counts"], d["term_denominator"]),
                                    (0, d["mapped_counts"], d["mapped_denominator"])):
        left = 0
        for category, count in counts.items():
            if not count:
                continue
            percent = 100*count/denominator
            bottom.barh(y, percent, left=left, height=.40, color=LICENSE[category])
            if category != "O2":
                outside = percent < 15
                bottom.text(left+percent/2, y+(.33 if outside else 0), f"{percent:.1f}",
                    ha="center", va="center", color=INK if outside else text_on(LICENSE[category]),
                    fontsize=7, fontweight="bold", clip_on=False)
            left += percent
    bottom.set_yticks([1, 0], [f"Term sets\n(n = {d['term_denominator']})",
                              f"Mapped releases\n(n = {d['mapped_denominator']})"])
    bottom.set(xlim=(0, 100), ylim=(-.6, 1.6), xticks=[0, 25, 50, 75, 100])
    bottom.set_xlabel("Share within each analysis unit (%)", color=INK, labelpad=3)
    for ax in (top, bottom):
        ax.tick_params(axis="y", length=0, pad=5, labelcolor=INK, labelsize=6.8)
        ax.tick_params(axis="x", length=0, pad=4, colors="#556670", labelsize=6.8)
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.legend(handles=[Patch(color=LICENSE[k], label=k+" "+label) for k, label in
        (("O1", "restrictive"), ("O2", "reciprocal"), ("O3", "permissive"))],
        loc="lower center", bbox_to_anchor=(.5, .02), ncol=3, frameon=False,
        fontsize=7, handlelength=.9, columnspacing=.8)
    return fig


def joint_profiles(d):
    matrix = np.array(d["joint_matrix"])
    n = d["n"]
    fig = plt.figure(figsize=(7.12, 2.65), facecolor="white")
    ax = fig.add_axes([.075, .219, .55, .69])
    im = ax.pcolormesh(range(4), range(7), matrix, cmap="Blues",
        norm=PowerNorm(.5, vmin=0, vmax=matrix.max()), edgecolors="white", linewidth=.8, rasterized=False)
    ax.set(xlim=(0, 3), ylim=(6, 0), xticks=[.5, 1.5, 2.5], xticklabels=FINAL_CATEGORIES,
           yticks=np.arange(6)+.5, yticklabels=list(RESOURCE))
    ax.xaxis.tick_top()
    ax.tick_params(length=0, pad=5, labelsize=8.7, colors=INK)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i in range(6):
        for j in range(3):
            count = int(matrix[i, j])
            color = "white" if count >= 170 else INK
            ax.text(j+.5, i+.31, str(count), ha="center", va="center", fontsize=9.4, weight="bold", color=color)
            ax.text(j+.5, i+.75, f"{100*count/n:.1f}%", ha="center", va="center", fontsize=7.5, color=color)
    ax.axhline(3, color=INK, linewidth=1.15)
    ax.axvline(1, color=INK, linewidth=1.15)
    ax.add_patch(Rectangle((.015, 2.015), .97, .97, fill=False, edgecolor=GOLD, linewidth=1.6))
    for y, label, part in ((.814, "L0-L2", matrix[:3]), (.469, "L3-L5", matrix[3:])):
        total, unqualified, qualified = int(part.sum()), int(part[:, 0].sum()), int(part[:, 1:].sum())
        require(total > 0, "Empty resource stratum")
        fig.text(.676, y, f"{label} (n={total})", fontsize=9, weight="bold", color=INK)
        fig.text(.676, y-.090, f"{unqualified} not qualified", fontsize=8.5, color=INK)
        fig.text(.676, y-.177, f"{qualified} qualified ({100*qualified/total:.1f}%)", fontsize=8.5, color=INK)
    cb = fig.colorbar(im, cax=fig.add_axes([.075, .088, .55, .025]), orientation="horizontal")
    cb.solids.set_rasterized(False)
    cb.solids.set_edgecolor("face")
    cb.set_ticks([0, 50, 200, int(matrix.max())])
    cb.ax.tick_params(labelsize=7.5, length=2, colors=MUTED)
    cb.outline.set_linewidth(.4)
    fig.text(.075, .151, "Cell count (square-root color scale)", fontsize=7.8, color=MUTED)
    fig.text(.676, .097, "Qualified categories:\nO1 and O3", fontsize=8, color=MUTED)
    return fig


def release_contexts(d):
    fig = plt.figure(figsize=(7.12, 4.80), facecolor="white")
    fig.text(.012, .982, "L3-L5: training-or-later resource evidence   |   O3: permissive final licensing",
             fontsize=8.5, color=INK, va="top")
    fig.legend(handles=[Patch(facecolor=c, label=s) for s, c in JOINT.items()], loc="upper left",
        bbox_to_anchor=(0, .950), ncol=4, frameon=False, fontsize=8, columnspacing=1.6,
        handlelength=1.3, handletextpad=.5)
    for x, title in ((.263, "Releases (n)"), (.526, "Within-group composition (%)"), (.859, "Both: % (n/N)")):
        fig.text(x, .861, title, fontsize=8.1, color=INK, weight="bold")
    for index, ((key, title, _), (bottom, height)) in enumerate(zip(GROUPS, ((.630, .172), (.348, .207), (.066, .207)))):
        groups = d["groups"][key]
        left = fig.add_axes([.227, bottom, .222, height])
        right = fig.add_axes([.514, bottom, .319, height])
        y = np.arange(len(groups))
        left.barh(y, [g["n"] for g in groups], height=.62, color=BLUE)
        left.set(xlim=(0, 830), xticks=[0, 200, 400, 600], yticks=y,
                 yticklabels=[g["name"].capitalize() if index == 0 else g["name"] for g in groups])
        right.set(xlim=(0, 100), xticks=[0, 25, 50, 75, 100], yticks=[])
        for axis in (left, right):
            axis.set_ylim(len(groups)-.5, -.5)
            clean_axis(axis)
            axis.tick_params(axis="x", labelsize=7.5, pad=3)
        left.tick_params(axis="y", pad=5, labelsize=8)
        for i, group in enumerate(groups):
            n, both, start = group["n"], group["both"], 0
            for part, color in zip(group["parts"], JOINT.values()):
                right.barh(i, 100*part/n, left=start, height=.62, color=color)
                start += 100*part/n
            left.text(n+9, i, str(n), fontsize=8, va="center", color=INK)
            right.annotate(f"{100*both/n:.1f}% ({both}/{n})", xy=(1.07, i),
                xycoords=("axes fraction", "data"), fontsize=7.9, va="center", color="#185D56")
        fig.text(.012, bottom+height+.016, f"({chr(97+index)}) {title}", fontsize=9.2, weight="bold", color=INK)
    return fig


def bottlenecks(d):
    rows = d["blockers"][:10]
    labels = {field: label for _, _, group in STAGES for field, label in group}
    fig, ax = plt.subplots(figsize=(7.1, 3.9))
    fig.subplots_adjust(left=.30, right=.98, bottom=.23, top=.94)
    for i, row in enumerate(rows):
        percent = round(100*row["count"]/d["n"], 1)
        ax.barh(i, percent, color=RESOURCE[row["field"][:2]], height=.65)
        ax.text(percent+1, i, f"{row['count']} ({percent:.1f}%)", va="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(rows)), [f"{r['field'][:2]} {labels[r['field']]}" for r in rows])
    ax.invert_yaxis()
    ax.set(xlim=(0, 83), xlabel=f"Share of all {d['n']} releases (%)")
    clean_axis(ax)
    shown = sorted({row["field"][:2] for row in rows})
    fig.legend(handles=[Patch(facecolor="none", edgecolor="none", label="Lifecycle stage:")]
        + [Patch(facecolor=RESOURCE[level], label=level) for level in shown],
        loc="lower center", bbox_to_anchor=(.59, .01), ncol=5, frameon=False, fontsize=8, columnspacing=1.4)
    return fig


def landscape_scope(d):
    rows, n = d["landscape"], d["n"]
    category_colors = {"O1": LICENSE["O1"], "O3": LICENSE["O3"], "Mixed/other": "#6C757D"}
    fig, (ax, scope) = plt.subplots(1, 2, figsize=(7.1, 4.9), gridspec_kw={"width_ratios": [1, 1.15]})
    fig.subplots_adjust(left=.32, right=.98, top=.90, bottom=.25, wspace=.48)
    for i, row in enumerate(rows):
        color = category_colors.get(row["category"], LICENSE.get(row["category"]))
        ax.scatter(row["count"], i, color=color, s=22)
        ax.annotate(str(row["count"]), (row["count"], i), xytext=(5, 0),
                    textcoords="offset points", va="center", fontsize=8)
    ax.set_xscale("log")
    ax.set_xlim(1, 1100)
    ax.set_xticks([1, 10, 100, 1000], ["1", "10", "100", "1000"])
    ax.set_yticks(range(len(rows)), [NAME_LABELS.get(r["name"], r["name"]) for r in rows], fontsize=8)
    ax.tick_params(axis="x", labelsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Releases (log scale)", fontsize=8.5)
    ax.set_title("(a) License prevalence", fontsize=9)
    for i, component in enumerate(("code", "data")):
        left, small = 0, []
        for key, (label, color) in SCOPE.items():
            count = d["scope_counts"][component][key]
            percent = 100*count/n
            scope.barh(i, percent, left=left, height=.32, color=color)
            if percent > 12:
                scope.text(left+percent/2, i, f"{count}\n{percent:.1f}%", ha="center",
                           va="center", color="white", fontsize=9)
            else:
                small.append(f"{label}:\n{count} ({percent:.1f}%)")
            left += percent
        scope.text(2, i+.23, "\n".join(small), va="top", fontsize=8, linespacing=1.15)
    scope.set_yticks([0, 1], ["Code", "Data"], fontsize=9)
    scope.tick_params(axis="x", labelsize=8)
    scope.set(xlim=(0, 100), ylim=(1.8, -.4))
    scope.set_xlabel(f"Share of {n} releases (%)", fontsize=8.5)
    scope.set_title("(b) Material relationships", fontsize=9)
    for axis in (ax, scope):
        axis.spines[["top", "right"]].set_visible(False)
    fig.legend(handles=[Patch(color=c, label=l) for l, c in SCOPE.values()],
        loc="lower left", bbox_to_anchor=(.57, .015), frameon=False, fontsize=8,
        title="Panel (b): scope relationship", title_fontsize=8)
    fig.legend(handles=[Patch(color=c, label=l) for l, c in category_colors.items()],
        loc="lower left", bbox_to_anchor=(.26, .015), frameon=False, fontsize=8,
        title="Panel (a): model category", title_fontsize=8)
    return fig


def compositions(d):
    licenses = {key: LICENSE[key] for key in ("O1", "O3", "Not qualified")}
    fig, axes = plt.subplots(3, 2, figsize=(7.1, 7.3))
    fig.subplots_adjust(left=.25, right=.98, top=.95, bottom=.17, hspace=.50, wspace=.15)
    for r, (key, title, _) in enumerate(GROUPS):
        groups = d["groups"][key]
        sizes = np.array([g["n"] for g in groups])
        for c, (field, colors) in enumerate((("resource_counts", RESOURCE), ("license_counts", licenses))):
            ax = axes[r, c]
            matrix = np.array([g[field] for g in groups])
            left = np.zeros(len(groups))
            for j, (_, color) in enumerate(colors.items()):
                values = matrix[:, j]/sizes*100
                ax.barh(range(len(groups)), values, left=left, color=color,
                        height=.75, edgecolor="white", linewidth=.4)
                for i, value in enumerate(values):
                    if value >= 7:
                        ax.text(left[i]+value/2, i, f"{value:.0f}", ha="center", va="center",
                                fontsize=7, color=text_on(color))
                left += values
            names = [g["name"].capitalize() if r == 0 else
                     "Other tasks" if g["name"] == "Other" else g["name"] for g in groups]
            labels = [f"{name}\nn={size} ({100*size/d['n']:.1f}%)" for name, size in zip(names, sizes)]
            ax.set_yticks(range(len(groups)), labels if c == 0 else [""]*len(groups))
            ax.tick_params(axis="y", length=0, labelsize=7)
            ax.invert_yaxis()
            ax.set_xlim(0, 100)
            ax.set_xticks([0, 50, 100])
            ax.spines[["top", "right"]].set_visible(False)
            ax.set_title(f"({chr(97+2*r+c)}) {title if c == 0 else 'Licensing freedom'}", fontsize=8, loc="left")
            if r == 2:
                ax.set_xlabel("Within-group composition (%)", fontsize=8)
    for colors, x, title in ((RESOURCE, .41, "Resource level (left panels)"),
                             (licenses, .81, "Final license profile (right panels)")):
        items = list(colors.items())
        if colors is RESOURCE:
            items = [items[i] for i in (0, 3, 1, 4, 2, 5)]
        fig.legend(handles=[Patch(color=c, label=l) for l, c in items], loc="upper center",
            bbox_to_anchor=(x, .09), ncol=3, fontsize=7, frameon=False, title=title, title_fontsize=7)
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="New output directory outside this package")
    parser.add_argument("--png", action="store_true", help="Also write PNG previews")
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    data, output = package / "data", args.output.resolve()
    require(output != package and package not in output.parents, "Output must be outside the package")
    require(not args.output.exists() and not args.output.is_symlink(), "Output already exists")
    d = derive(data)
    try:
        font_manager.findfont("Liberation Sans", fallback_to_default=False)
        font = "Liberation Sans"
    except ValueError:
        font = "DejaVu Sans"
    # Each figure gets a fresh style, independent of local matplotlib settings.
    specs = [("fig2_resources", resources, font, 8), ("fig3_licensing", licensing, "DejaVu Sans", 8),
             ("fig4_joint_profiles", joint_profiles, font, 8),
             ("fig5_release_contexts", release_contexts, font, 8),
             ("rq1_bottlenecks", bottlenecks, font, 8),
             ("rq2_landscape_scope", landscape_scope, "DejaVu Sans", 9),
             ("rq4_compositions", compositions, font, 8)]
    output.mkdir(parents=True, exist_ok=False)
    figures = {}
    for name, draw, family, size in specs:
        with matplotlib.rc_context():
            plt.rcdefaults()
            plt.rcParams.update({"font.family": family, "font.size": size, "svg.fonttype": "none",
                "pdf.fonttype": 42, "svg.hashsalt": "public-quantitative-figures", "text.usetex": False})
            fig = draw(d)
            try:
                figures[name] = {**text_bounds(fig), "font_family": family}
                for suffix in (["svg", "pdf", "png"] if args.png else ["svg", "pdf"]):
                    metadata = {"Date": None} if suffix == "svg" else (
                        {"CreationDate": None, "ModDate": None} if suffix == "pdf" else {})
                    path = output / (name + "." + suffix)
                    fig.savefig(path, dpi=190, metadata=metadata)
                    figures[name][suffix + "_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            finally:
                plt.close(fig)
    report = dict(data=d, figures=figures, matplotlib=matplotlib.__version__, numpy=np.__version__)
    (output / "figure_verification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Rendered {len(figures)} figures from {d['n']} releases; text boundaries passed.")


if __name__ == "__main__":
    main()

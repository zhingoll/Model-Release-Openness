# Model Release Openness: Structured Data and Analysis

This repository accompanies "Beyond Open Weights: Measuring Artifact-Level
Reuse Support in High-Attention Public Model Releases."

This package contains the structured data used to analyze resource completeness
and licensing freedom in 845 model releases, together with the independent
Human86 test set. The analysis uses retained judgments to reproduce resource
and license distributions, joint profiles, group comparisons, validation
metrics, and sensitivity results.

## Reproduce the Results

Use Python 3.10 or later. The analysis uses the Python standard library and
runs offline. From this directory, run:

```sh
python3 reproduce.py --output ../reproduced-results
python3 check_support.py
```

Choose a new output directory outside this package. `reproduce.py` verifies input
checksums, checks record coverage and cross-file consistency, recomputes the
statistics, and compares selected outputs with the retained study results.
Successful execution prints `PASS` and creates `verification.json` in the
output directory. The other output files contain the recomputed statistics.

`DATA_DICTIONARY.md` explains the data and denominators. Input files are in
`data/`; retained comparison results are in `expected/`. `manifest.json`
records the SHA-256 checksum of each distributed input, document, and script.
The analysis computes results from `data/` before checking them against
`expected/`.

`check_support.py` checks rule coverage, source-provenance joins, adjudication
explanation coverage, and the MRBOM example against the distributed data.

## Reproduce the Figures

Install the dependencies in `requirements-figures.txt`, then run:

```sh
python3 -m pip install -r requirements-figures.txt
python3 render_figures.py --output ../reproduced-figures
```

The renderer reads the structured data and produces editable SVG and vector
PDF files for the seven quantitative figures in the main paper and supplement.
Add `--png` for previews. Use a new output directory outside the package.
Figure 1 is the method diagram, provided as the editable source
`assets/fig1_architecture.svg`. The figure dependencies are separate from
the standard-library numerical replay.

## Read the Method and Evidence

`METHOD.md` explains the measurement and aggregation rules.
`ANNOTATION.md` describes the annotation procedure and label records.
`EVIDENCE.md` explains the source links, recorded versions, checksums, and
public adjudication explanations. `PROMPTS.md` introduces the preserved
Verifier and Challenger template pair. The rule tables, inference settings,
and MRBOM schema and example are in `method/`.

## Scope

The formal sample contains 845 officially associated Hugging Face releases
selected from weekly top-100 lists of like-count increments observed from
3 March 2025 to 9 March 2026, after de-duplication and eligibility screening.
Human86 contains 86 releases and
22 fields per release, giving 1,892 comparisons with independent expert
reference labels. The constant-prediction baseline and the two anonymized
rater label sets support the accompanying validation analyses.

The license analysis links releases to reviewed term sets and their coded
rights, obligations, restrictions, and material scope. Separate files contain
the data-license audit and the inputs to resource sensitivity analyses.
These sensitivity inputs are applied to separate copies of the measurement
records; the primary labels remain unchanged.

Source URLs and field-to-source links identify the materials associated with
resource judgments. The package reproduces analyses and figures from retained
judgments offline; a new online REMAP prediction run is a separate task.

## License and Third-Party Materials

The author-created code, documentation, figures, and research data in this
package are licensed under Apache-2.0. See `LICENSE` for the complete terms,
`NOTICE` for author attribution, and `LICENSING.md` for file coverage and
third-party exclusions.

Third-party documents remain at their source locations. Their content is
subject to the terms of the respective rights holders. This package does
not grant redistribution rights for those documents.

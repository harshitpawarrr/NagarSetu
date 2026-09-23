# Held-Out Labelled Test Dataset

This directory contains curated, ground-truth-labelled evaluation sets used exclusively to benchmark NagarSetu performance.

## Evaluation Rules
1. **Strict Hold-Out**: Records here must never be used to construct prompt examples, training data, or tuning datasets.
2. **Ground Truth Labels**: Each record must contain verified ground-truth values for:
   - `true_department`
   - `true_category`
   - `true_urgency`
   - `true_ward`
   - `true_duplicate_group`
3. **Reproducibility**: Evaluation runs must report exact macro/micro accuracy, agreement matrices, and duplicate reduction ratios against these test files. Never fabricate benchmark metrics.

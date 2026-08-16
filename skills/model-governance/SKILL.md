---
name: model-governance
description: Assess whether a model serving issue is data drift, concept drift, model version regression, or upstream data corruption, and recommend the right governance action.
metadata:
  version: "0.1.0"
  maturity: demo
---

# Model Governance

## Purpose

Use this skill to decide the model-side root cause category and recommend the right governance action (rollback, retrain, data refresh, or hold) for an Edge AIOps incident.

## Inputs

- RCA candidates from `log-trace-rca`.
- Model version history and the active vs. desired version.
- Drift score time series and ground-truth label availability.
- OTA update timeline.

## Procedure

1. Compare the active model version against the desired version. If they differ recently, suspect version regression.
2. If version matches, check the drift score trend. A sustained drift_score > threshold suggests data drift.
3. If drift score is normal but accuracy on labeled samples dropped, suspect concept drift or upstream data corruption.
4. Recommend the matching governance action: rollback, retrain on recent data, hold for human review, or escalate.
5. Always cite the evidence used for the classification.

## Output Contract

```json
{
  "classification": "version_regression",
  "active_version": "resnet50-v3.2.1",
  "desired_version": "resnet50-v3.2.0",
  "drift_score": 0.12,
  "drift_threshold": 0.20,
  "recommended_action": "rollback_to_v3.2.0",
  "evidence": ["ota_applied_v3.2.1_at_13:55", "accuracy_dropped_from_0.92_to_0.71"]
}
```

## Quality Gates

- Never recommend rollback without comparing active vs. desired version.
- Never recommend retrain if ground-truth labels are unavailable — surface it as a data gap instead.
- If classification is ambiguous, output `uncertain` and recommend human review.
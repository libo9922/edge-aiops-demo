---
name: recovery-verify
description: Verify that the edge fleet and model serving have recovered after remediation, and produce postmortem plus observability improvement notes.
metadata:
  version: "0.1.0"
  maturity: demo
---

# Recovery Verify

## Purpose

Use this skill to confirm that the executed remediation actions actually restored the SLOs and that no residual risk remains. Produce a postmortem and list observability improvements.

## Inputs

- Remediation plan with per-action risk decisions.
- After-incident metrics (accuracy, latency, error rate, fleet health).
- Synthetic probe results.
- Active model version vs. desired model version.

## Procedure

1. Compare before and after metrics for every SLO listed in the plan.
2. Check the active model version against the desired version.
3. Run synthetic probes against the affected endpoints.
4. Inspect remaining nodes for any residual risk (stranded OTA, stale config).
5. If any SLO is not met, mark `recovered: false` and recommend the next action.
6. Write postmortem notes (root cause, what worked, what didn't) and observability suggestions.

## Output Contract

```json
{
  "recovered": true,
  "verification": {
    "inference_accuracy": 0.91,
    "p99_latency_ms": 420,
    "fleet_health": "healthy",
    "active_model_version": "resnet50-v3.2.0"
  },
  "residual_risk": [],
  "postmortem_notes": [
    "OTA fan-out skipped canary stage, allowed regression to reach production fleet.",
    "Ground-truth labels were not collected hourly, delaying drift detection."
  ],
  "observability_improvements": [
    "Add 5% canary stage before full OTA fan-out.",
    "Collect ground-truth labels every hour and publish drift score."
  ]
}
```

## Quality Gates

- Never mark `recovered: true` unless all SLOs in the plan are met.
- Postmortem notes must include at least one process improvement and one observability improvement.
- Residual risk must always be either an empty list or a list of concrete risks.
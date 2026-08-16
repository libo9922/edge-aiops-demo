---
name: alert-fusion
description: Fuse model drift signals, edge node alerts, and customer complaints into a single incident candidate for Edge AIOps triage.
metadata:
  version: "0.1.0"
  maturity: demo
---

# Alert Fusion

## Purpose

Use this skill when an agent receives noisy model drift alerts, edge node health events, and customer complaints and must decide whether they describe one incident or separate events.

## Inputs

- Customer or operator complaint text and timestamp.
- Alert list with model, node ID, severity, metric name, value, unit, and timestamp.
- Before-incident metric snapshot.
- Optional ticket metadata such as region, model version, and owner.

## Procedure

1. Normalize timestamps, node IDs, model names, version strings, and severity labels.
2. Group signals that share a time window, affected node region, model name, or symptom.
3. Derive the primary incident candidate with severity, affected nodes, models, symptoms, and timeline.
4. Preserve every source reference so downstream RCA can cite the evidence.
5. If key fields are missing (e.g., model version, ground-truth labels), keep the signal but add a data gap instead of discarding it.

## Output Contract

```json
{
  "severity": "P1",
  "affected_nodes": ["edge-hangzhou-03"],
  "affected_models": ["resnet50-v3.2.1"],
  "timeline": [{"time": "14:02", "event": "model_drift_detected", "evidence_ref": "alert:DRIFT-2001"}],
  "symptoms": ["resnet50::accuracy_drop=0.92→0.71"],
  "evidence_refs": ["alert:DRIFT-2001"],
  "data_gaps": ["ground_truth_labels_for_last_24h"]
}
```

## Quality Gates

- Do not merge unrelated alerts only because they are close in time.
- Do not downgrade severity when user-facing impact and P1 alerts are present.
- Every symptom must map back to an alert, complaint, or metric source.
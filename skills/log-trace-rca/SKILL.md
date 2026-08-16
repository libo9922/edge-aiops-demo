---
name: log-trace-rca
description: Correlate edge node logs, distributed traces, model serving metrics, OTA events, and node resource pressure to rank root cause candidates.
metadata:
  version: "0.1.0"
  maturity: demo
---

# Log-Trace RCA

## Purpose

Use this skill to find the most likely root cause of an edge incident by correlating heterogeneous evidence: container logs, inference traces, model metrics, OTA update history, and node resource snapshots.

## Inputs

- Anomaly Detection incident summary.
- Edge node logs (container runtime, inference server, GPU driver).
- Distributed traces (gateway → inference → backend).
- Model serving telemetry (latency p99, throughput, drift score).
- OTA update history (timestamps, model versions, node IDs).
- Node resource snapshot (CPU, memory, GPU, network).

## Procedure

1. Build a unified timeline from logs, traces, OTA events, and metric anomalies.
2. Identify the earliest symptom and trace it forward through the call chain.
3. For each candidate cause (OTA regression, data drift, node resource, network), collect at least one supporting and one refuting piece of evidence.
4. Compute a confidence score based on evidence count, specificity, and recency.
5. Report the top candidate plus 2-4 alternatives, each with evidence and confidence.

## Output Contract

```json
{
  "top_candidate": {
    "cause": "ota_model_regression",
    "confidence": 0.86,
    "evidence": [
      "trace:trace-inf-2001 latency spike at 14:01",
      "model:resnet50 v3.2.1 deployed 13:55",
      "log:OTA applied v3.2.1 at 13:55"
    ],
    "refuting": ["node cpu 38% (normal)"]
  },
  "alternatives": [
    {"cause": "data_drift", "confidence": 0.10, "evidence": ["drift_score stable"]},
    {"cause": "node_resource", "confidence": 0.04, "evidence": ["mem 41% (normal)"]}
  ],
  "missing_evidence": ["ground_truth_labels_for_last_24h"]
}
```

## Quality Gates

- Every candidate must have at least one piece of evidence.
- If two causes have similar confidence, report both instead of arbitrarily picking one.
- Never invent log lines or metric values; if evidence is missing, report a data gap.
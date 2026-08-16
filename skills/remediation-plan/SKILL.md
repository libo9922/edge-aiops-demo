---
name: remediation-plan
description: Convert RCA and model governance results into ordered remediation actions, validation steps, and rollback points for the edge fleet.
metadata:
  version: "0.1.0"
  maturity: demo
---

# Remediation Plan

## Purpose

Use this skill to turn a confirmed root cause and governance recommendation into a concrete, ordered, risk-aware remediation plan for the edge fleet.

## Inputs

- Top RCA candidate and confidence.
- Model governance recommendation (rollback, retrain, hold).
- Available rollback points (previous model version, last known-good OTA, snapshot).
- Per-action risk classification from `risk-guard`.

## Procedure

1. Enumerate candidate actions: rollback model, quarantine node, fan-out OTA, drain traffic, scale inference pool.
2. Order actions so that pre-conditions are satisfied first (e.g., drain before reboot).
3. For each action, record the target, parameters, risk level, and approval requirement.
4. Define validation checks that prove recovery (accuracy threshold, latency SLO, fleet health).
5. Define the rollback point to revert to if validation fails.

## Output Contract

```json
{
  "risk_level": "L2",
  "auto_execute": false,
  "actions": [
    {
      "step": 1,
      "type": "quarantine_node",
      "target": "edge-hangzhou-03",
      "risk_level": "L1",
      "approval_required": false
    },
    {
      "step": 2,
      "type": "rollback_model",
      "target": "resnet50",
      "from_version": "v3.2.1",
      "to_version": "v3.2.0",
      "risk_level": "L2",
      "approval_required": true
    }
  ],
  "validation": ["inference_accuracy >= 0.88 within 5 min", "node_health = healthy"],
  "rollback_point": "model:resnet50@v3.2.0"
}
```

## Quality Gates

- Every action must have an explicit target and parameters.
- High-risk actions (L2/L3) must be marked `approval_required: true`.
- The rollback point must always reference an existing artifact (model version, OTA, snapshot).
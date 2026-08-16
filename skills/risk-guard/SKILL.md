---
name: risk-guard
description: Classify remediation actions by risk level (L0-L3) and decide whether auto-execution is permitted.
metadata:
  version: "0.1.0"
  maturity: demo
---

# Risk Guard

## Purpose

Use this skill to assign a risk level to every remediation action and decide whether the Recovery Verifier may execute it without human approval.

## Inputs

- Candidate remediation action (type, target, parameters).
- Active blast radius: number of affected nodes, customer tier, model criticality.
- Time of day and on-call schedule.

## Procedure

1. Assign a base risk level by action type:
   - L0: read-only diagnostics (probe, log query)
   - L1: local scope, reversible (quarantine single node, drain traffic on one node)
   - L2: fleet-wide or model-affecting (rollback model, fan-out OTA to < 10 nodes)
   - L3: cross-region or irreversible (delete snapshot, force re-train, region failover)
2. Adjust upward if customer tier is P0 or the action is outside business hours.
3. Adjust downward only if the action is fully reversible within 60 seconds.
4. Mark `auto_execute: true` only for L0 and L1 actions after adjustment.

## Output Contract

```json
{
  "action": "rollback_model",
  "target": "resnet50",
  "base_level": "L2",
  "adjusted_level": "L2",
  "reasons": ["model_affects_5_nodes", "p0_customer_region"],
  "auto_execute": false,
  "approval_required": true
}
```

## Quality Gates

- Never auto-execute an L2 or L3 action, even if reversible.
- Always cite the reason for any level adjustment.
- If the on-call schedule is unknown, fail closed (require approval for L1+).
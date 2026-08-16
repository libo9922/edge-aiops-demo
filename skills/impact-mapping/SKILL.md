---
name: impact-mapping
description: Map an alert cluster to affected edge nodes, deployed models, user-facing SLOs, and severity for Edge AIOps triage.
metadata:
  version: "0.1.0"
  maturity: demo
---

# Impact Mapping

## Purpose

Use this skill to translate a cluster of fused alerts into the concrete blast radius: which edge nodes are affected, which model versions are deployed there, and what user-facing SLOs are at risk.

## Inputs

- Fused alert cluster from `alert-fusion`.
- Fleet registry: node ID → region → deployed model versions.
- Model serving SLOs (accuracy, latency p99, throughput).
- Region-level customer tier.

## Procedure

1. Resolve each alert to one or more node IDs and model versions via the fleet registry.
2. For each model version, look up the active SLO contract.
3. If any node is in a P0/P1 customer region, escalate severity by one level.
4. If more than 30% of nodes serving the same model are affected, mark it as fleet-wide impact.
5. Produce an impact map with affected nodes, models, SLOs, and user tiers.

## Output Contract

```json
{
  "affected_nodes": ["edge-hangzhou-03"],
  "affected_models": ["resnet50-v3.2.1"],
  "user_facing_slos_at_risk": ["inference_accuracy >= 0.88", "p99_latency <= 800ms"],
  "customer_tier": "P0",
  "severity": "P1",
  "fleet_wide": false
}
```

## Quality Gates

- Never mark a node as affected without evidence from an alert, log, or metric.
- Always cite the source alert that established the link.
- If the fleet registry is stale or missing, surface it as a data gap.
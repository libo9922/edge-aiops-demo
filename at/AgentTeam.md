# Edge AIOps Demo Team

This directory describes the Edge AIOps multi-agent team that AgentTeams will instantiate.

## Renamed Agents

| Old name (opspilot-aligned) | New name (Edge AIOps-flavored) | Stage |
|-----------------------------|---------------------------------|-------|
| `anomaly_detection_agent`   | **`edge_sentinel`**            | detect |
| `rca_analyst_agent`         | **`edge_diagnostician`**       | analyze |
| `remediation_planner_agent` | **`edge_orchestrator`**        | plan |
| `recovery_verifier_agent`   | **`edge_sentry`**              | verify |

The new names reflect the **edge + model + OTA** signal surface, not generic ITSM triage.

## Topology

```
ops_manager (AgentTeams Manager)
   └── ops_team_leader (TeamLeader)
         ├── edge_sentinel          (decision-support: alert-fusion, impact-mapping)
         ├── edge_diagnostician    (decision-support: log-trace-rca, model-governance)
         ├── edge_orchestrator     (execution-request: remediation-plan, risk-guard)
         └── edge_sentry           (verification: recovery-verify, model-governance)
```

## Execution Model — Agents Decide, Operators Execute

This demo does **not** call K3s / Prometheus / MLflow / Argo Rollouts directly. The split is intentional:

| Layer | What lives there | Examples |
|-------|------------------|----------|
| **AgentTeams** (decision) | Observe, attribute, plan, verify | 4 business agents + Skills |
| **Mock executor** (request queue) | Files structured execution requests with risk level | `mock_executor.create_action_request` |
| **External Operator** (execution, NOT in demo) | Performs the side effect when L2/L3 is approved | K8s Operator, ML Platform Operator, OTA controller |

Why this split?

- LLM calls are slow + non-deterministic → never on the hot path of high-risk ops.
- L2/L3 actions must be **human-approved** before any Operator runs them.
- The mock executor queue (`GET /tools/{scenario_id}/requests`) is the **HITL seam**.

## Workflow Model

The workflow is declared as a **dependency graph** in `team_spec.json` (`dependency_graph`) and mirrored as K8s CRDs in `team_spec.yaml`. AgentTeams v1.2 dispatches tasks respecting those dependencies at runtime.

```
edge_sentinel ──▶ edge_diagnostician ──▶ edge_orchestrator ──▶ edge_sentry
   detect             analyze                plan                verify
                                                       │
                                                       ▼
                                            mock_executor.create_action_request
                                                       │
                                            ┌──────────┴──────────┐
                                            ▼                     ▼
                                    L0/L1: auto_approved    L2/L3: pending_approval
                                                              │
                                                              ▼
                                                          Human approver
                                                              │
                                                              ▼
                                                    External Operator (out of demo)
```

Adding a new agent (e.g., `security_auditor` between `edge_diagnostician` and `edge_orchestrator`) only requires appending a new task to `dependency_graph`; the Manager re-plans automatically.

## Map to opspilot-zero-demo

| opspilot-zero-demo | edge-aiops-demo (renamed) | Stage | Tool category |
|--------------------|---------------------------|-------|---------------|
| `alert-intake`     | `edge_sentinel`           | detect | decision-support |
| `rca-analyst`      | `edge_diagnostician`      | analyze | decision-support |
| `remediation-planner` | `edge_orchestrator`    | plan | execution-request |
| `recovery-verifier` | `edge_sentry`            | verify | verification |

The architecture, role split, and Skills-to-Agent mapping mirror the proven pattern
while specializing the content and execution model for the Edge AIOps domain.
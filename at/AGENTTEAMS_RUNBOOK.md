# AgentTeams Runbook — Edge AIOps Demo

This runbook describes how to run the Edge AIOps demo inside AgentTeams. It mirrors the `opspilot-zero-demo` runbook so reviewers familiar with that demo can ramp up quickly.

## 1. Prerequisites

- Python 3.10+ (only for the mock tool gateway).
- AgentTeams runtime v1.2+ (provides Manager, TeamLeader, and Worker CRDs).
- Local clone of this repository.
- Network reachability from the worker runtime to the tool gateway host.

## 2. Start the Mock Tool Gateway

```bash
cd edge-aiops-demo/tools
python mock_tool_server.py --host 0.0.0.0 --port 18090
```

Verify:

```bash
curl http://127.0.0.1:18090/health
curl http://127.0.0.1:18090/scenarios
```

Expected scenarios: `model_drift`, `edge_node_failure`.

## 3. Environment Variables

Point the worker runtime at the tool gateway:

```bash
export EDGE_AIOPS_TOOL_GATEWAY_URL="http://127.0.0.1:18090"
```

## 4. Team Spec

Two flavors ship in `at/`:

- `team_spec.json` — declarative JSON form with `dependency_graph`.
- `team_spec.yaml` — K8s CRD form (`Team` + `Worker` resources), directly `kubectl apply -f` ready.

Both declare:

- 1 Manager (`ops_manager`)
- 1 TeamLeader (`ops_team_leader`)
- 4 business agents: `edge_sentinel`, `edge_diagnostician`, `edge_orchestrator`, `edge_sentry`
- 1 scenario adapter (`scenario_runner`)

Workflow is declared as `dependency_graph`. The Manager (per AgentTeams v1.2 semantics) decides the actual dispatch order; we do not hard-code a linear pipeline.

## 5. Run a Scenario

### 5.1 Model Drift (default)

```text
User: Run the Edge AIOps demo with scenario `model_drift`.
```

Expected agent chain:
1. `edge_sentinel` → fuses 3 alerts into `INC-2001`.
2. `edge_diagnostician` → top candidate `ota_model_regression`, confidence 0.86.
3. `edge_orchestrator` → files **2 execution requests**:
   - `quarantine_node` L1 → `auto_approved`
   - `rollback_model` L2 → `pending_approval` + approval ticket
4. `edge_sentry` → verifies that auto-approved requests produced metrics improvement; flags pending-approval requests as `reason: "L2 requires human approval"`.

### 5.2 Edge Node Failure

```text
User: Run scenario `edge_node_failure`.
```

Expected agent chain:
1. `edge_sentinel` → fuses 3 alerts into `INC-2002`.
2. `edge_diagnostician` → top candidate `edge_node_failure`.
3. `edge_orchestrator` → files quarantine + throttle requests (mix of L1/L2).
4. `edge_sentry` → verifies auto-approved portion; reports pending-approval portion.

## 6. Inspect the Request Queue

The mock executor queue is the HITL seam. Inspect it:

```bash
curl http://127.0.0.1:18090/tools/model_drift/requests
```

Each request has:

- `request_id`
- `action_type` (`rollback_model`, `quarantine_node`, `schedule_update`, etc.)
- `target`
- `parameters`
- `risk_level` (`L0`–`L3`)
- `status` (`auto_approved` | `pending_approval`)
- `submitted_by` (always `edge_orchestrator`)

Reset between runs:

```bash
curl -X POST http://127.0.0.1:18090/tools/model_drift/reset
```

Inspect the full tool trace (every Tool call with timestamp):

```bash
curl http://127.0.0.1:18090/tools/model_drift/trace
```

## 7. From Demo to Production

This demo does **not** call K3s / Prometheus / MLflow / Argo Rollouts. The split is intentional:

- **In-demo**: AgentTeams makes decisions and files structured requests.
- **Out-of-demo (production)**: An external Operator polls the same request queue, performs the side effect, and updates status. L2/L3 must additionally receive human approval first.

Production migration checklist:

1. Replace `mock_executor.create_action_request` with an HTTP / MCP call to the request queue.
2. Stand up the external Operator (K8s / ML platform / OTA).
3. Wire the approval ticket (`mock_ticket.create_approval_task`) to your real ITSM (e.g., Jira/ServiceNow).
4. Swap `mock_monitoring`, `mock_logs`, `mock_traces` for real telemetry backends **without changing Agent contracts**.

The Agent code never changes during this migration — only the mock gateway is replaced.

## 8. Open-Source Contributions Plan

Aligned with competition scoring:

| Dimension | Contribution |
|-----------|--------------|
| Skill engineering | Publish Skills as versioned frontmatter with quality gates and a shared `SKILL.md` template. |
| MCP adapter | Publish `mock_executor` and the other 9 mock tools as MCP servers without changing the Agent contract. |
| Team Harness best practice | Document the 4-stage dependency graph as a reusable template (in `at/AgentTeam.md`). |
| Agent Loop evaluation | Contribute per-agent rubrics (correctness, evidence citation, safety) and a shared evaluation harness. |

See `README.md` § "Open-source plan" for details.
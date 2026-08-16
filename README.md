# Edge AIOps Demo — Multi-Agent Incident Response for Edge + AI Fleets

A minimal, reproducible example of the AgentTeams `Manager → TeamLeader → 4 business agents` pattern, specialized for **edge node fleets + model registry + OTA pipelines**. Mirrors the proven `opspilot-zero-demo` shape, but with Edge AIOps-flavored naming and a clean **agents-decide / operators-execute** split.

---

## 1. Problem statement

Modern enterprise AI deployments span:

- **Edge nodes**: thousands of distributed inference servers with intermittent connectivity.
- **Model registry**: dozens of model versions rolling out via OTA.
- **OTA pipeline**: fan-out updates across regions and customer tiers.
- **Drift signals**: accuracy regression, concept drift, data drift, upstream corruption.

When an incident hits — say a bad OTA causes accuracy regression on a region — the on-call team must:

1. Detect that model drift and edge degradation are linked.
2. Rank the root cause: OTA regression vs. data drift vs. node failure vs. network.
3. Plan a safe remediation: rollback, quarantine, canary.
4. Verify recovery via metrics and synthetic probes.

Doing this manually is slow and error-prone. A multi-agent team with explicit Skills and risk policy can do it faster, more safely, and more auditable.

---

## 2. Why a multi-agent team

| Concern | Multi-agent answer |
|---------|---------------------|
| **Separation of concerns** | Each agent owns one stage: detect / analyze / plan / verify. |
| **Risk policy enforcement** | `risk-guard` Skill classifies actions L0-L3; the executor applies L0/L1 auto-approved vs L2/L3 pending-approval. |
| **Evidence lineage** | Every output cites evidence_refs; data gaps are surfaced, never guessed. |
| **Skill reuse** | Skills are domain-agnostic (`alert-fusion`, `risk-guard`); edge-specific content lives in Agent/Skill files. |
| **HITL seam** | L2/L3 actions create approval tickets; humans approve before the external Operator runs them. |

---

## 3. Architecture

```
ops_manager  (AgentTeams Manager)
   └── ops_team_leader  (TeamLeader)
         ├── edge_sentinel          (decision-support: alert-fusion, impact-mapping)
         ├── edge_diagnostician    (decision-support: log-trace-rca, model-governance)
         ├── edge_orchestrator     (execution-request: remediation-plan, risk-guard)
         └── edge_sentry           (verification: recovery-verify, model-governance)
```

Workflow is declared as a **dependency graph** in `at/team_spec.json` (`dependency_graph`) and mirrored as K8s CRDs in `at/team_spec.yaml`. AgentTeams v1.2 dispatches tasks respecting those dependencies at runtime.

---

## 4. The split that matters: agents decide, operators execute

This demo does **not** call K3s / Prometheus / MLflow / Argo Rollouts directly.

| Layer | Lives in | Purpose |
|-------|----------|---------|
| **AgentTeams** | demo | Observe, attribute, plan, verify |
| **Mock executor queue** | demo | Files structured requests with risk level + status |
| **External Operator** | **out of demo (production)** | Performs the side effect after L2/L3 is human-approved |

Why?

- LLM calls are slow + non-deterministic → never on the hot path of high-risk ops.
- L2/L3 actions must be **human-approved** before any Operator runs them.
- The executor queue (`GET /tools/{scenario_id}/requests`) is the **HITL seam** that lets the same Agent code survive the demo-to-production migration unchanged.

---

## 5. Agent naming (Edge AIOps flavor)

| Old name (opspilot-aligned) | New name (Edge AIOps) | Stage | Tool category |
|-----------------------------|------------------------|-------|---------------|
| `anomaly_detection_agent`   | **`edge_sentinel`**   | detect | decision-support |
| `rca_analyst_agent`         | **`edge_diagnostician`** | analyze | decision-support |
| `remediation_planner_agent` | **`edge_orchestrator`** | plan | **execution-request** |
| `recovery_verifier_agent`   | **`edge_sentry`**     | verify | verification |

The new names reflect the **edge + model + OTA** signal surface, not generic ITSM triage.
`edge_orchestrator` is the only agent that files execution requests.

---

## 6. Repository layout

```
edge-aiops-demo/
├── README.md
├── at/
│   ├── team_spec.json         # declarative JSON, dependency graph
│   ├── team_spec.yaml         # K8s CRD mirror (Team + Worker resources)
│   ├── AgentTeam.md           # topology + execution-model diagram
│   └── AGENTTEAMS_RUNBOOK.md  # how to run + inspect the demo
├── agents/
│   ├── edge-sentinel/Agent.md
│   ├── edge-diagnostician/Agent.md
│   ├── edge-orchestrator/Agent.md
│   └── edge-sentry/Agent.md
├── skills/
│   ├── alert-fusion/SKILL.md
│   ├── impact-mapping/SKILL.md
│   ├── log-trace-rca/SKILL.md
│   ├── model-governance/SKILL.md
│   ├── remediation-plan/SKILL.md
│   ├── risk-guard/SKILL.md
│   └── recovery-verify/SKILL.md
├── tools/
│   ├── mock_tool_server.py    # HTTP mock tool gateway
│   ├── mock_tools.py          # deterministic in-process state
│   └── tool_catalog.json      # tool whitelist + future MCP mapping
└── scenarios/
    ├── model_drift.json       # OTA regression → accuracy drop
    └── edge_node_failure.json # unreachable + thermal nodes → fleet degradation
```

---

## 7. Quickstart

```bash
cd tools
python mock_tool_server.py --host 0.0.0.0 --port 18090

# In another shell:
export EDGE_AIOPS_TOOL_GATEWAY_URL="http://127.0.0.1:18090"

# In AgentTeams UI or kubectl:
#   kubectl apply -f at/team_spec.yaml
#   ask: "Run the Edge AIOps demo with scenario `model_drift`."
```

Reset and inspect:

```bash
curl -X POST http://127.0.0.1:18090/tools/model_drift/reset
curl http://127.0.0.1:18090/tools/model_drift/requests   # execution requests filed
curl http://127.0.0.1:18090/tools/model_drift/trace      # full tool call trace
```

---

## 8. Scenarios

### 8.1 `model_drift`

- **Trigger**: OTA rollout of `resnet50 v3.2.1` without canary stage on Hangzhou fleet.
- **Symptoms**: accuracy 0.92 → 0.71, p99 latency 420 → 1450 ms, drift score above threshold.
- **Expected top candidate**: `ota_model_regression` (confidence ~0.86).
- **Expected filed requests**:
  - `quarantine_node` L1 → `auto_approved`
  - `rollback_model` L2 → `pending_approval` + approval ticket
- **Expected verification**: with auto-approved request, accuracy 0.71 → 0.91, p99 → 420 ms, fleet healthy. Pending-approval request is **not** executed (mock just records it).

### 8.2 `edge_node_failure`

- **Trigger**: Edge node `edge-shanghai-02` unreachable + `edge-shanghai-05` GPU thermal critical.
- **Symptoms**: throughput 12 qps, latency 1850 ms.
- **Expected top candidate**: `edge_node_failure`.
- **Expected filed requests**: quarantine + throttle (mix of L1/L2).
- **Expected verification**: auto-approved portion improves metrics; pending-approval portion is reported but not executed.

---

## 9. Skills (versioning + quality gates)

Each Skill ships with:

- YAML frontmatter: `name`, `description`, `version`, `maturity`.
- Inputs and procedure (numbered steps).
- Output contract as a JSON Schema-style snippet.
- Quality gates that the agent must satisfy when calling the Skill.

Example from `risk-guard/SKILL.md`:

> Never auto-execute an L2 or L3 action, even if reversible. Always cite the reason for any level adjustment.

This pattern (frontmatter + procedure + output contract + gates) is exactly the Skill engineering rubric the competition rewards.

---

## 10. Real-data roadmap (final-stage bonus only)

This demo deliberately depends **only** on the mock executor queue. Real-data integration is a **final-stage bonus**, not a demo prerequisite.

| Phase | When | Mock data | Real data |
|-------|------|-----------|-----------|
| Initial demo | this commit | 2 JSON scenarios + mock executor | — |
| Final bonus (optional) | pre-final | — | K3s single-node + Triton inference + Prometheus scrape for live demo only |

We do not pre-commit to K3s / Prometheus / MLflow / Argo because the production stack belongs to the deployer. The mock executor's request queue is the **stable interface** that any Operator can plug into.

---

## 11. Open-source plan

| Dimension | Planned contribution |
|-----------|----------------------|
| Skill engineering | Publish the seven Skills as a reference set with quality gates and a shared `SKILL.md` template. |
| MCP adapter | Publish the 11 mock tools as MCP servers (especially `mock_executor`) without changing the Agent contract. |
| Team Harness best practice | Document the 4-stage dependency graph + agents-decide/operators-execute split as a reusable template (in `at/AgentTeam.md`). |
| Agent Loop evaluation | Contribute per-agent rubrics (correctness, evidence citation, safety) and a shared evaluation harness. |

This addresses the competition scoring: scenario value (25%), multi-agent collaboration (25%), Skill engineering (25%), engineering validation (20%), open source (5%).

---

## 12. Why this design is right-sized

- **4 business agents**, not 7: each owns one stage of a strict dependency graph. Mirrors `opspilot-zero-demo` so reviewers can compare directly.
- **7 Skills**, not 12: each is small, named after the decision it makes, and has a clear input/output contract.
- **11 mock tools**: 8 decision-support + 2 execution-request + 1 verification. No direct execution.
- **2 scenarios**: one for OTA regression, one for edge node failure — both realistic, both verifiable.
- **DAG-ready workflow**: declared as `dependency_graph`; adding a 5th agent (e.g., `security_auditor`) is a 3-line change in `team_spec.json`, no Agent code touched.
- **Stable demo-to-prod interface**: the mock executor queue is the same shape an external Operator would consume.

The team is large enough to demonstrate real collaboration, small enough to be auditable end-to-end, and clean enough to survive the leap from mock to production.
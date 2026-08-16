# Final-Stage Roadmap — Edge AIOps Real-Protocol Integration

This document describes how the demo (`v0.3.0`) graduates to a final-stage
production-grade submission by replacing the mock executor with **real Operators
that consume the same request queue**, and plugging real telemetry backends into
the decision-support tools. **Agent contracts do not change.**

---

## 0. Goal

| Demo (v0.3.0) | Final stage |
|---------------|-------------|
| `mock_executor.create_action_request` records request | External Operator **performs** the action |
| `mock_monitoring.query_metrics` returns canned JSON | Prometheus **scrapes** real Triton + K3s |
| `mock_logs.search_logs` returns canned list | OTel Collector **streams** container logs |
| `mock_traces.query_traces` returns canned list | Jaeger / Tempo **stores** distributed traces |
| `mock_model.get_version_history` returns canned list | MLflow **lists** real model versions |
| `mock_ota.list_recent_updates` returns canned list | Argo Rollouts **lists** real Rollouts |
| `mock_fleet.list_nodes` returns canned list | K3s / KubeEdge kubelet **lists** real nodes |
| `mock_runbook.search` returns keyword match | Lightweight RAG over real Runbook corpus |

The interface contracts stay **byte-identical**. The mock layer is swapped, not
the Agent code.

---

## 1. Architecture Delta

```
                v0.3.0 (demo)                       Final stage
┌────────────────────────────────────┐    ┌────────────────────────────────────┐
│           AgentTeams               │    │           AgentTeams               │
│  edge_sentinel → diagnostician →   │    │  (same prompts, same Skills)       │
│  orchestrator → sentry             │    │                                    │
└─────────────────┬──────────────────┘    └─────────────────┬──────────────────┘
                  │ mock gateway                              │ mock gateway
                  ▼                                           ▼
       ┌──────────────────────┐                  ┌──────────────────────────┐
       │   LocalMockTools     │                  │   RealAdapters (delegate)│
       │   - canned JSON      │                  │   - PrometheusAdapter    │
       │   - in-process state │                  │   - OTelAdapter          │
       │   - request queue    │                  │   - MlflowAdapter        │
       └──────────────────────┘                  │   - ArgoAdapter          │
              │                                  │   - K3sAdapter           │
              │ GET /requests                    │   - KB RAG adapter       │
              ▼                                  └──────────┬───────────────┘
    ┌──────────────────────┐                                │ HTTP / MCP / gRPC
    │  (demo ends here)    │                                ▼
    └──────────────────────┘                  ┌──────────────────────────┐
                                              │  Real backends (laptop)  │
                                              │  - K3s single-node       │
                                              │  - Triton inference      │
                                              │  - Prometheus + Grafana  │
                                              │  - OTel Collector        │
                                              │  - Jaeger                │
                                              │  - MLflow                │
                                              │  - Argo Rollouts         │
                                              │  - MinIO (model registry)│
                                              └──────────┬───────────────┘
                                                         │
                                                         ▼
                                              ┌──────────────────────────┐
                                              │  External Operator Pool  │
                                              │  - K8s Operator          │
                                              │  - ML Platform Operator  │
                                              │  - OTA Operator          │
                                              │  - Node Operator         │
                                              │  - Probe Operator        │
                                              └──────────────────────────┘
```

The Operator Pool **is the missing piece in v0.3.0**. The demo intentionally
leaves it out because building it requires real infrastructure. For final stage,
this is where the heavy engineering goes.

---

## 2. Real-Protocol Wiring Plan (per tool)

### 2.1 `mock_monitoring` → PrometheusAdapter

| Aspect | Detail |
|--------|--------|
| Backend | Prometheus v2.50+ |
| Endpoint | `GET http://prom:9090/api/v1/query_range` |
| Required scrape targets | Triton inference (`triton_inference_requests_total`, `triton_inference_latency_ms`), K3s kubelet (`node_cpu_seconds_total`), OTA controller (`rollout_phase`), MLflow (`model_version_stage`) |
| Implementation | Replace `LocalMockTools.query_metrics()` body with `requests.get(prom_url + "/api/v1/query_range", params={"query": expr, "start": start, "end": end, "step": step})` |
| Risk | Prometheus can be flaky; add 3s timeout + retry |
| Time | **1 day** |

### 2.2 `mock_logs` / `mock_traces` → OTelAdapter

| Aspect | Detail |
|--------|--------|
| Backend | OpenTelemetry Collector + Jaeger / Tempo |
| Endpoint | `POST http://otel:4318/v1/logs` (OTLP HTTP), `GET http://jaeger:16686/api/traces` |
| Required sources | K3s container logs, Triton access logs, MLflow audit logs |
| Implementation | For logs: tail JSON files written by Fluent Bit. For traces: Jaeger query API |
| Risk | Log volume; filter at Collector side |
| Time | **1 day** |

### 2.3 `mock_model` → MlflowAdapter

| Aspect | Detail |
|--------|--------|
| Backend | MLflow Tracking Server v2.16+ |
| Endpoint | `POST http://mlflow:5000/api/2.0/mlflow/model-versions/search` |
| Required state | At least 3 model versions registered: `resnet50 v3.2.0`, `v3.2.1` (buggy), `v3.2.0-canary` |
| Implementation | `requests.post(mlflow_url + "/api/2.0/mlflow/model-versions/search", json={"filter": f"name='{model}'"})` |
| Risk | MLflow auth token handling |
| Time | **1 day** |

### 2.4 `mock_ota` → ArgoAdapter

| Aspect | Detail |
|--------|--------|
| Backend | Argo Rollouts v1.7+ on K3s |
| Endpoint | `GET /apis/rollouts/v1alpha1/namespaces/edge/rollouts` |
| Required CRs | `Rollout` for `resnet50` with canary steps |
| Implementation | `requests.get(argo_url + "/apis/rollouts/v1alpha1/namespaces/edge/rollouts")` + bearer token from kubeconfig |
| Risk | K8s RBAC; need ServiceAccount with `rollouts:get` |
| Time | **1-2 days** |

### 2.5 `mock_fleet` / `mock_node` → K3sAdapter

| Aspect | Detail |
|--------|--------|
| Backend | K3s v1.28+ single-node cluster (laptop) + simulated edge nodes |
| Endpoint | `GET https://k3s:6443/api/v1/nodes` |
| Required state | 3 fake nodes (`edge-hangzhou-03`, `edge-shanghai-02`, `edge-shanghai-05`) created via `kubectl` or scripted |
| Implementation | Use `kubernetes` Python client with kubeconfig |
| Risk | kubeconfig in CI; use service account token |
| Time | **2-3 days** |

### 2.6 `mock_runbook` → Lightweight RAG

| Aspect | Detail |
|--------|--------|
| Backend | ChromaDB / FAISS in-memory + sentence-transformers embedding |
| Corpus | Internal Runbook markdown files (10-50 docs typical) |
| Endpoint | `POST /api/search` (local FastAPI) |
| Implementation | At build time, chunk + embed Runbook markdown; at query time, embed query + cosine-similarity top-K |
| Risk | First-run embedding cost (~10s for 50 docs); acceptable |
| Time | **2 days** |

### 2.7 `mock_probe` → real synthetic probe

| Aspect | Detail |
|--------|--------|
| Backend | A small k6 / vegeta / wrk2 harness |
| Endpoint | Local script that POSTs sample inference requests to Triton |
| Implementation | Shell out to `vegeta attack -duration=30s -rate=10 -targets=probe.json` |
| Risk | Probe must not pollute real metrics |
| Time | **1 day** |

---

## 3. External Operator Pool (NEW for final stage)

Each Operator is a long-running Python / Go service that:
1. Polls `GET /tools/{scenario}/requests` (or a real MQ topic in production).
2. Picks up `auto_approved` requests matching its `action_type`.
3. Performs the side effect via the real backend.
4. Updates request status (`executed` / `failed`).
5. For `pending_approval` requests, waits for the approval ticket to flip before
   picking up.

| Operator | action_types | Backend call |
|----------|--------------|--------------|
| **K8sOperator** | `quarantine_node`, `drain_node` | K3s `PATCH /api/v1/nodes/{id}` (cordon + taint) |
| **MLPlatformOperator** | `rollback_model`, `transition_stage` | MLflow `POST /model-versions/transition-stage` |
| **OTAOperator** | `schedule_update`, `abort_rollout` | Argo Rollouts `PATCH .../rollouts/{name}` |
| **NodeOperator** | `restart_inference`, `scale_pool` | Triton control API or K3s Deployment scale |
| **ProbeOperator** | `synthetic_probe` | vegeta / k6 run, parse output |

Implementation in **Go** for K8sOperator and MLPlatformOperator (because of mature
client libraries), **Python** for the others.

Time budget: **5-7 days** for all 5 operators + tests.

---

## 4. Infrastructure Stack (laptop-deployable)

| Component | How it runs on a laptop |
|-----------|-------------------------|
| K3s | `curl -sfL https://get.k3s.io \| sh -` |
| Triton Inference Server | Docker container, `nvcr.io/nvidia/tritonserver:24.06-py3` |
| Prometheus | Docker container, `prom/prometheus:v2.50.0` |
| OTel Collector | Docker container, `otel/opentelemetry-collector:0.93.0` |
| Jaeger | Docker container, `jaegertracing/all-in-one:1.54` |
| MLflow | Docker container, `ghcr.io/mlflow/mlflow:v2.16.0` + Postgres backend |
| Argo Rollouts | `kubectl apply -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml` |
| MinIO | Docker container, `minio/minio:latest` (for MLflow artifacts) |

Total: **~10 Docker containers**, fits on 32GB RAM laptop with GPU.

---

## 5. Live Demo Scenario (final stage)

Reproduce `model_drift` end-to-end with real infra:

```
T0:  Push resnet50 v3.2.1 (buggy) via MLflow → trigger Argo Rollout to edge-hangzhou-03
T1:  K3s rollout proceeds without canary (intentionally misconfigured)
T2:  Triton serves v3.2.1; Prometheus sees accuracy drop 0.92 → 0.71
T3:  Alertmanager fires: model_drift_alert + ota_completed_alert
T4:  AgentTeams triggers EdgeSentinel
T5:  EdgeDiagnostician ranks ota_model_regression (confidence 0.86)
T6:  EdgeOrchestrator files:
       - quarantine_node L1 → auto_approved → K8sOperator cordons edge-hangzhou-03
       - rollback_model L2 → pending_approval → ticket created in Jira
T7:  Human approves in Jira → status flips to approved
T8:  MLPlatformOperator transitions model v3.2.1 → Archived, v3.2.0 → Production
T9:  EdgeSentry queries Prometheus after-metrics → accuracy 0.91, fleet healthy
T10: Postmortem auto-generated; Runbook RAG surfaces 3 past OTA regressions
```

Wall-clock budget for live demo: **8-12 minutes**.

---

## 6. Engineering Validation Checklist (final stage)

| Item | Status when done |
|------|------------------|
| All 7 demo Skills unchanged (semantic & version stable) | ✅ |
| 11 mock tools replaced by real adapters | ✅ |
| External Operator Pool (5 operators) handles L0-L3 | ✅ |
| End-to-end live demo runs in ≤12 minutes | ✅ |
| Failure injection: kill Operator mid-execution → request stays `pending`, no zombie state | ✅ |
| OTel traces visible in Jaeger for every Agent invocation | ✅ |
| LoongSuite / AgentScope Studio integration for Agent Loop | ✅ |
| Request queue + approval ticket audit trail replayable | ✅ |
| All evidence_refs in Agent output resolve to real Prometheus / OTel / MLflow / Argo URLs | ✅ |

---

## 7. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM API rate limit during live demo | Medium | Demo blocks | Pre-record Agent run as fallback |
| K3s laptop failure | Low | Infra down | Have docker-compose backup stack on second laptop |
| Argo Rollouts RBAC mis-config | Medium | OTA broken | Run RBAC verifier script pre-demo |
| MLflow stage transition race | Medium | Rollback fails twice | Idempotent operator with retry + status check |
| LLM hallucination in RCA | Medium | Wrong root cause | evidence_refs gate + human-in-the-loop on top candidate |
| Demo exceeds 12 min | High | Time pressure | Pre-recorded video fallback; live demo optional |

---

## 8. Time Plan

| Week | Deliverable |
|------|------------|
| Week 1 | K3s single-node + Triton + Prometheus + Grafana stack up; Scenario 1 (model_drift) replayable with real telemetry |
| Week 2 | MLflow + Argo Rollouts + OTel + Jaeger stack; External Operator Pool (5 ops) implemented; Scenario 2 (edge_node_failure) replayable end-to-end |
| Week 3 | Lightweight RAG over Runbook; LoongSuite OTel / AgentScope Studio integration; full live demo rehearsal |
| Week 4 | Final hardening: failure-injection tests, RBAC verification, evidence URL generation, demo recording |

---

## 9. Open-Source Plan (final stage)

Same as demo plan, but with concrete PRs:

| PR target | Content |
|-----------|---------|
| `agentscope-ai/AgentTeams` | Add `docs/examples/edge-aiops.md` (this demo as reference) |
| `agentscope-ai/AgentTeams` | Add `Skill` template generator (from our 7 Skills' frontmatter) |
| `agentscope-ai/AgentScope` | Submit LoongSuite OTel hook for Agent invocation tracing |
| `agentscope-ai/MCP` | Submit `edge_aiops_mcp` server (wraps the 11 mock tools as MCP) |
| `argoproj/argo-rollouts` | Submit RBAC example for `Rollout` controller in edge namespace |

---

## 10. Success Criteria (final stage)

The final submission is considered production-grade when:

1. **Live demo** runs without human intervention beyond approval clicks.
2. **Every evidence_refs** in Agent output resolves to a real, clickable URL.
3. **Every execution_request** is auditable end-to-end (Agent → request queue → Operator → backend → status).
4. **Failure injection** (kill Operator, kill K3s node, corrupt MLflow DB) demonstrates the system degrades safely.
5. **Open-source PRs** at least 2 merged into upstream repos.

---

## 11. What this demo (v0.3.0) already gives you

The demo is the **sealed contract** the final stage is built against. Specifically:

- `dependency_graph` in `team_spec.json` is the workflow the Manager dispatches.
- `Output Contract` in each `Agent.md` is the inter-agent payload schema.
- `mock_executor.create_action_request` is the **stable request shape** any Operator must accept.
- `tools/tool_catalog.json` is the **stable tool whitelist** any real adapter must satisfy.

So the migration from demo → final is purely a backend swap, not a redesign.
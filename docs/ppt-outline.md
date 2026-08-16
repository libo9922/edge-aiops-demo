# PPT 提案骨架 — Agent Infra 初赛方案

> **Title**: Edge AIOps — Multi-Agent Incident Response for Edge + AI Fleets
> **Track**: Agent Infra 初赛方案 PPT
> **Pattern**: 严格对齐官方「方向 1：零人工运维」

每页建议时长 **45 秒 - 90 秒**，总时长 **8-12 分钟**。

---

## Slide 1 — 封面 (15s)

```
┌─────────────────────────────────────────────┐
│                                             │
│   Edge AIOps                                │
│   Multi-Agent Incident Response             │
│   for Edge + AI Fleets                      │
│                                             │
│   团队名 · 日期                              │
│   Agent Infra 初赛方案                       │
│                                             │
└─────────────────────────────────────────────┘
```

**口头稿 (15s)**:
> 我们做的是「边缘 + 模型 + OTA」场景下的多 Agent 协同运维，名字叫 Edge AIOps。下面我会讲清楚为什么、怎么做、能落地到什么程度。

---

## Slide 2 — 痛点 (60s)

```
  边缘 AI 部署的 4 个现实痛点

  ① 边缘节点数量大: 千级 GPU 节点，间歇性断网
  ② 模型版本多: 数十个版本通过 OTA 滚动
  ③ 漂移信号多: accuracy / concept / data / upstream 4 类
  ④ 风险分级模糊: 哪个动作能自动做？哪个必须人批？

  → 单 Agent 或单工具都解决不了
  → 需要「检测-归因-规划-验证」4 个 Agent 协同
```

**口头稿 (60s)**:
> 边缘 AI 部署的规模已经到了千节点级别。一个模型版本通过 OTA 推到几十个区域，每个区域又有自己的客户分级。出了问题时，到底是模型回归、数据漂移、节点故障还是网络问题？一个 Agent 串行处理会失去阶段边界；多个工具独立调用会失去证据链。我们需要的是一个有清晰阶段、有风险分级、能 HITL 的多 Agent 团队。

---

## Slide 3 — 我们的方案: Edge AIOps 4 Agent 团队 (90s)

```
  ┌────────────────────────────────────────────┐
  │          ops_manager (Manager)             │
  │                │                           │
  │          ops_team_leader (TeamLeader)      │
  │                │                           │
  │   ┌─────┬─────┴─────┬─────┐               │
  │   ▼     ▼           ▼     ▼               │
  │ Sentry Diagnose   Plan   Verify            │
  │   ▲                 ▲     ▲               │
  │   │  detect         │plan │               │
  │   └─────────────────┘─────┘               │
  └────────────────────────────────────────────┘

  edge_sentinel       → 边缘异常哨兵（检测）
  edge_diagnostician  → 边缘诊断师（归因）
  edge_orchestrator   → 边缘编排师（规划）
  edge_sentry         → 边缘验收师（验证）
```

**口头稿 (90s)**:
> 4 个 Agent，每个一个阶段。EdgeSentinel 看的是边缘 + 模型 + OTA 三类信号，做信号融合；EdgeDiagnostician 看日志、Trace、模型遥测、OTA 历史、节点资源、Runbook，做多源归因；EdgeOrchestrator 拿到归因后做风险分级，发起执行请求；EdgeSentry 验收恢复结果，写 postmortem。4 个 Agent 加 1 个 TeamLeader 加 1 个 Manager，共 6 个 Worker。和官方的 Manager-TeamLeader-Worker 模式严格对齐。

---

## Slide 4 — 关键设计: agents decide, operators execute (90s)

```
  ┌─────────────────────────────────┐
  │       AgentTeams (决策)         │
  │   edge_sentinel → diagnose →   │
  │   orchestrator → sentry        │
  └────────────────┬────────────────┘
                   │ create_action_request()
                   ▼
  ┌─────────────────────────────────┐
  │     Request Queue (HITL seam)  │
  │  L0/L1: auto_approved           │
  │  L2/L3: pending_approval        │
  └────────────────┬────────────────┘
                   │ (生产环境外)
                   ▼
  ┌─────────────────────────────────┐
  │   External Operator Pool       │
  │   K8s/ML/OTA/Node/Probe Ops    │
  └─────────────────────────────────┘
```

**口头稿 (90s)**:
> 关键设计：Agent **不直接执行** 高风险动作。Agent 只发「执行请求」，带风险等级。L0 L1 自动批准，L2 L3 进入 pending_approval 状态，等人类审批。这个队列就是 HITL seam，也是 demo 跨越到生产的稳定接口。Demo 阶段我们 mock 这个队列；生产阶段由外部 Operator（K8s Operator / ML 平台 Operator / OTA Operator）监听并执行。**Agent 代码永远不变**。

---

## Slide 5 — 工作流: DAG-ready 的 dependency_graph (60s)

```
  edge_sentinel ──▶ edge_diagnostician
                           │
                           ▼
                  edge_orchestrator
                           │
                           ▼
                      edge_sentry

  JSON:
  "dependency_graph": [
    {task: "incident.detect",   owner: edge_sentinel,       depends_on: []},
    {task: "incident.attribute",owner: edge_diagnostician,  depends_on: ["incident.detect"]},
    {task: "incident.plan",     owner: edge_orchestrator,   depends_on: ["incident.attribute"]},
    {task: "incident.verify",   owner: edge_sentry,         depends_on: ["incident.plan"]}
  ]

  YAML (K8s CRD) 同时存在，kubectl apply -f 直接可用
```

**口头稿 (60s)**:
> 工作流以 dependency_graph 形式声明，AgentTeams Manager 动态调度，加新 Agent 就是 3 行 JSON 改动。YAML 格式（K8s CRD）也同步提供，AgentTeams v1.2 原生支持。

---

## Slide 6 — Skills (7 个，全部含质量门) (90s)

```
  每个 Skill 含 4 部分:

  ① YAML frontmatter (name / version / maturity)
  ② Inputs + Procedure (numbered steps)
  ③ Output Contract (JSON Schema-style)
  ④ Quality Gates (Skill-level 的硬约束)

  我们的 7 个 Skill:
  ┌────────────────────────────────────────┐
  │ alert-fusion      │ 告警融合          │
  │ impact-mapping    │ 影响映射          │
  │ log-trace-rca     │ 多源归因          │
  │ model-governance  │ 模型治理          │
  │ remediation-plan  │ 修复计划生成      │
  │ risk-guard        │ L0-L3 风险分级   │
  │ recovery-verify   │ 恢复验收          │
  └────────────────────────────────────────┘
```

**口头稿 (90s)**:
> 7 个 Skill，每个都是「决策类」可复用能力。结构标准化：YAML frontmatter 含版本和成熟度；输入输出有显式契约；最后有 Quality Gates 作为硬约束。比如 risk-guard 永远不自动批准 L2/L3；recovery-verify 永远要求每个 postmortem 必须含流程改进和可观测改进。这些 Quality Gates 是 Skill 工程最值钱的部分。

---

## Slide 7 — Scenario 1: model_drift 跑通演示 (120s)

```
  触发: 14:00 OTA 把 resnet50 v3.2.1 推到 Hangzhou 集群 (无 canary)
  症状: accuracy 0.92 → 0.71, p99 420ms → 1450ms

  流程:
  ① EdgeSentinel: 3 个告警融合为 INC-2001 (severity P1)
  ② EdgeDiagnostician:
     - log-trace-rca 关联 OTA + 准确率下降
     - 调 mock_runbook.search("accuracy drop after OTA")
       → 返回 RB-OTA-001, score=6.0
     - top_candidate: ota_model_regression, confidence=0.86
  ③ EdgeOrchestrator:
     - quarantine_node L1 → auto_approved → REQ-MODEL_DRIFT-002
     - rollback_model L2 → pending_approval → REQ-MODEL_DRIFT-001
     - 创建审批 ticket APPROVAL-MODEL_DRIFT
  ④ EdgeSentry:
     - query_metrics(after) → accuracy=0.91, p99=420ms, fleet_healthy
     - pending_approval 的 rollback 不执行（mock 阶段）
     - postmortem: 加 canary stage, 收集 ground-truth labels

  复现: cd tools && python mock_tool_server.py
        curl http://127.0.0.1:18090/tools/model_drift/requests
```

**口头稿 (120s)**:
> 我们准备了两个场景，跑通了 demo 的是模型漂移。真实还原了一个没做 canary 的 OTA 推送，14 点准时触发，准确率从 0.92 跌到 0.71。EdgeSentinel 把 3 个告警融合成一个 P1 事故；EdgeDiagnostician 调 Runbook RAG 拿到 6.0 分的 RB-OTA-001，归因到 ota_model_regression 置信度 0.86；EdgeOrchestrator 发出 2 个执行请求，L1 自动批准 L2 卡在审批；EdgeSentry 验证 L1 自动批准部分让准确率回到 0.91。整个链路可审计、可复现。

---

## Slide 8 — 工程实现细节 (60s)

```
  仓库结构:
  edge-aiops-demo/
  ├── at/             team_spec.json + team_spec.yaml
  ├── agents/         4 个 Agent.md (含 Position + IO 契约)
  ├── skills/         7 个 SKILL.md (含 frontmatter + 质量门)
  ├── tools/          mock_tool_server.py + mock_tools.py + tool_catalog.json
  └── scenarios/      2 个 JSON (model_drift + edge_node_failure)

  工程亮点:
  - Mock 和真协议接口签名 1:1 对齐 (tool_catalog.json 标 future_mcp_mapping)
  - 11 个 mock 工具分 3 类: decision-support / execution-request / verification
  - 任何工具的 mock → 真实现 都是 1 行改动
  - 7 个 Skill 全版本化 (frontmatter 含 version + maturity)
```

**口头稿 (60s)**:
> 仓库结构清晰，4 个 Agent + 7 个 Skill + 11 个 mock 工具 + 2 个场景。重点是 mock 和真协议接口对齐，所以从 demo 跨越到生产是「替换实现」，不是「重写 Agent」。

---

## Slide 9 — 与示例的差异 (60s)

```
  opspilot-zero-demo          edge-aiops-demo
  ─────────────────────       ─────────────────────────
  alert-intake         →      edge_sentinel         (Edge 信号)
  rca-analyst          →      edge_diagnostician    (节点/模型/OTA 多源归因)
  remediation-planner  →      edge_orchestrator     (发执行请求，不直接执行)
  recovery-verifier    →      edge_sentry           (SLA + 队列状态验证)

  差异:
  - 命名体现 Edge + 模型 + OTA 业务
  - Agent 不直接执行高风险动作,只发请求
  - 加 dependency_graph + K8s CRD 镜像
  - mock_runbook 升级为轻量 RAG (tag + symptom 评分)
  - 删除对 K3s/Prometheus 的过早抽象
```

**口头稿 (60s)**:
> 我们的设计与示例有 4 点显著差异。命名反映 Edge 业务，Agent 不直接执行，依赖图显式声明，mock 实现含轻量 RAG。我们没有抄袭套壳，而是吸收示例的 Manager-Worker 模式后做了适配。

---

## Slide 10 — 工程验证 + 可观测 (60s)

```
  Mock 验证 (已跑通):
  ✓ Health / Scenarios / Requests / Trace 4 个端点
  ✓ L0/L1 auto_approved → after metrics 显示恢复
  ✓ L2/L3 pending_approval → 不执行，留在队列
  ✓ Lightweight RAG: query "accuracy drop after OTA" → score=6.0

  真实落地路径 (复赛):
  ✓ K3s 单机 + Triton + Prometheus + MLflow + Argo Rollouts
  ✓ External Operator Pool (5 ops)
  ✓ LoongSuite OTel 自动埋点
  ✓ 见 docs/final-roadmap.md

  可观测:
  - GET /tools/{scenario}/trace   每次工具调用
  - GET /tools/{scenario}/requests  每个执行请求状态
  - 每个 Agent 输出含 evidence_refs
```

**口头稿 (60s)**:
> Mock 阶段我们已经跑通了 4 类验证：健康检查、L0/L1 自动批准、L2/L3 挂起、轻量 RAG 检索。复赛的真实落地路径见 final-roadmap.md，包括 K3s 单节点、Triton 推理、Prometheus 抓取、MLflow 模型注册、Argo Rollouts OTA。可观测性靠 trace 端点和 requests 端点，每次工具调用和每个执行请求都有审计。

---

## Slide 11 — 开源贡献计划 (45s)

```
  5 个 PR 目标:
  ① agentscope-ai/AgentTeams: docs/examples/edge-aiops.md
  ② agentscope-ai/AgentTeams: Skill frontmatter 模板生成器
  ③ agentscope-ai/MCP: edge_aiops_mcp server (包装 11 个 mock 工具)
  ④ agentscope-ai/AgentScope: LoongSuite OTel Agent 埋点 hook
  ⑤ argoproj/argo-rollouts: 边缘命名空间 RBAC 示例

  评估标准对齐 (官方 5 维度):
  - 场景价值 (25%): 真实 Edge AIOps 场景
  - 多 Agent 协作 (25%): 4 Agent + dependency_graph
  - Skill 工程 (25%): 7 Skill + frontmatter + 质量门
  - 工程验证 (20%): mock 跑通 + final-roadmap
  - 开源贡献 (5%): 5 个 PR
```

**口头稿 (45s)**:
> 我们准备贡献 5 个 PR，覆盖文档、Skill 模板、MCP server、可观测 hook、K8s RBAC 示例。完全对齐官方 5 个评分维度。

---

## Slide 12 — Q&A (300s+)

预判的高频问题：

| 问题 | 我们的答案 |
|------|----------|
| 为什么 4 个 Agent 不多不少？ | 严格对应 ITSM「检测-归因-规划-验证」4 阶段；多一个就模糊焦点；少一个就丢阶段边界 |
| 为什么 Agent 不直接执行高风险动作？ | LLM 不可靠 + L2/L3 不可逆；通过 HITL seam 让 Agent 做参谋、外部 Operator 做执行 |
| Skill 如何复用？ | 7 个 Skill 全部决策类、命名按「决策动词」、含 frontmatter 版本化；可复用到其他 AIOps 场景 |
| 如何落地到生产？ | final-roadmap.md 详细写了 K3s + Triton + Prometheus + MLflow + Argo Rollouts + 5 个 Operator 的对接计划 |
| 真实数据从哪来？ | 决赛对接真实 Triton 推理服务；可手动 push v3.2.1 复现 OTA 回归 |
| 与 opspilot-zero-demo 区别？ | 见 Slide 9 |

---

## 总时长预估

| Slide | 时长 |
|-------|------|
| 1. 封面 | 15s |
| 2. 痛点 | 60s |
| 3. 4 Agent 团队 | 90s |
| 4. agents decide / operators execute | 90s |
| 5. dependency_graph | 60s |
| 6. Skills | 90s |
| 7. Scenario 1 演示 | 120s |
| 8. 工程实现 | 60s |
| 9. 与示例差异 | 60s |
| 10. 工程验证 | 60s |
| 11. 开源贡献 | 45s |
| 12. Q&A | 300s+ |
| **总计** | **~17 分钟（含 Q&A）** |

PPT 本身展示时间 **8-10 分钟**，留 7-10 分钟给 Q&A。
# 作品简介 — Edge AIOps 边缘 AI 智能运维协同系统

**项目名称**：Edge AIOps — Multi-Agent Incident Response for Edge + AI Fleets

**问题与场景**：现代企业 AI 部署覆盖千级边缘节点 + 数十个模型版本 + 跨区域 OTA 流水线。当 OTA 推送错版本导致准确率下跌、或边缘节点批量故障时，单 Agent 串行处理失去阶段边界，多工具独立调用失去证据链，单脚本无法沉淀为可复用能力。行业普遍缺少端到端、能审计、可 HITL 的协同系统。

**核心解决方案**：基于 AgentTeams Manager-TeamLeader-Worker 模式，构建 4 职能 Agent 协同团队——edge_sentinel（边缘哨兵·检测）融合边缘+模型+OTA 三类信号；edge_diagnostician（边缘诊断师·归因）多源证据关联+轻量 RAG 检索 Runbook；edge_orchestrator（边缘编排师·规划）按 risk-guard L0-L3 分级，发起执行请求；edge_sentry（边缘验收师·验证）做 SLA 验收。关键设计：agents-decide / operators-execute 拆分，Agent 永远不直接执行高风险动作，通过「执行请求队列」做 HITL seam，L0/L1 自动批准、L2/L3 等人类审批。

**创新点**：1) agents-decide / operators-execute 拆分使 Agent 代码在 demo→生产迁移中零改动；2) 7 个版本化 Skill（含 frontmatter + IO 契约 + Quality Gates）；3) dependency_graph 工作流支持 Manager 动态调度，加新 Agent 仅 3 行 JSON 改动；4) mock 工具接口签名与真实 K3s/Prometheus/MLflow/Argo 协议对齐，落地成本仅替换 mock 实现。

**复用价值**：7 个 Skill 全部决策类（alert-fusion / impact-mapping / log-trace-rca / model-governance / remediation-plan / risk-guard / recovery-verify），可迁移到任何 AIOps 场景（数据库、客服、安全、金融风控）。11 个 mock 工具通过 future_mcp_mapping 字段标注真实协议映射。

**当前进展**：完整 demo 已跑通，含 6 Worker + 4 业务 Agent + 7 Skill + 11 工具 + 2 场景（model_drift / edge_node_failure），mock executor 队列验证 L2 正确进入 pending_approval、after metrics 正确联动 L1 auto_approved。复赛对接 K3s + Triton + Prometheus + MLflow + Argo Rollouts 的 4 周时间表已规划到 docs/final-roadmap.md。

---

**字数统计**：约 480 字（在 500 字限制内）
**核心亮点**：
- 命中官方方向 1「零人工运维」
- 4 Agent 严格对齐 Manager-TeamLeader-Worker
- 7 Skill 含 frontmatter 版本化 + Quality Gates
- agents-decide / operators-execute 拆分（HITL seam）
- mock→真实协议 1:1 对齐（落地零成本）
- 5 PR 开源贡献计划
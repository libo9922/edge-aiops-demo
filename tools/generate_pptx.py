"""Generate Edge AIOps submission PPTX by editing the official template.

Strategy: load `/workspace/Agent Infra初赛方案PPT框架模板.pptx`, walk through
every text frame, replace the placeholder strings with our content, and save
to `docs/edge-aiops-submission.pptx`. All decorative shapes (rounded boxes,
accent lines, icons) are preserved.

Run:
    python tools/generate_pptx.py
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict

from pptx import Presentation
from pptx.util import Emu, Pt


TEMPLATE = Path("/workspace/Agent Infra初赛方案PPT框架模板.pptx")
OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "edge-aiops-submission.pptx"


# ----------------------------------------------------------------------
# Per-slide replacement rules
# Keyed by the EXACT placeholder string in the template.
# When matched, the text_frame text is set to the replacement value.
# ----------------------------------------------------------------------

REPLACEMENTS: Dict[str, str] = {
    # ---- Slide 1: Cover ----
    "GOAI世界人工智能开源大赛": "GOAI 世界人工智能开源大赛 · Agent Infra 赛道",
    "初赛方案 PPT | 内容框架模板": "Edge AIOps — Multi-Agent Incident Response",
    "初赛方案 PPT": "Edge AIOps — Multi-Agent Incident Response",
    "内容框架模板": "",
    "Datawhale · 参赛选手参考资料": "libo9922 · 团队名",
    "Agent Infra 新智基座 初赛 · 方案 PPT 模板": "Edge AIOps · 边缘 + 模型 + OTA 智能运维协同",

    # ---- Slide 2: 一页纸速览 ----
    "P0 · 一页纸速览": "P0 · 一页纸速览",
    "作品简介": "作品简介",
    "项目名称": "项目名称",
    "≤ 20 字。一句话说清「为谁、解决什么」。": "≤ 20 字 · 一句话说清「为谁、解决什么」",
    "【在此填写项目名称】": "Edge AIOps 边缘 AI 智能运维",
    "问题与场景": "问题与场景",
    "目标用户是谁、在什么场景、现实痛点是什么。": "目标用户是谁、在什么场景、现实痛点是什么",
    "【描述真实场景与核心痛点】": (
        "边缘 AI 部署千级 GPU 节点 + 数十模型版本 + OTA 流水线。"
        "事故时单 Agent 串行失去阶段边界，多工具独立调用失去证据链。"
    ),
    "核心解决方案": "核心解决方案",
    "一句话讲清整体思路：用多 Agent + Skill 怎么解。": "一句话讲清整体思路：用多 Agent + Skill 怎么解",
    "【概述端到端解决方案】": (
        "4 职能 Agent（检测 / 归因 / 规划 / 验证）+ 7 决策类 Skill；"
        "agents-decide / operators-execute 拆分，HITL seam 做 L2/L3 审批。"
    ),
    "创新点与差异化": "创新点与差异化",
    "对比现有做法，你独特/更优在哪。": "对比现有做法，你独特 / 更优在哪",
    "【列 1–2 个关键差异化优势】": (
        "① Agent 不直接执行高风险动作，demo→生产代码零改动；"
        "② 7 Skill 全部版本化 + 质量门 + 轻量 RAG。"
    ),
    "开放 / 复用价值": "开放 / 复用价值",
    "可复用成果、能迁移到哪些场景。": "可复用成果、能迁移到哪些场景",
    "【说明复用与迁移价值】": (
        "7 个决策类 Skill 可迁移到任何 AIOps 场景；"
        "11 个 mock 工具接口与真协议对齐，落地仅替换实现。"
    ),
    "当前进展": "当前进展",
    "做到了什么程度、有无可运行成果。": "做到了什么程度、有无可运行成果",
    "【说明当前完成度与里程碑】": (
        "完整 demo 跑通：6 Worker + 4 Agent + 7 Skill + 11 工具 + 2 场景；"
        "复赛 4 周 roadmap 已规划到 docs/final-roadmap.md。"
    ),

    # ---- Slide 4: 第一章扉页 (kept as-is, already official) ----
    "第一章": "第一章",
    "场景与价值": "场景与价值",
    "对应评分维度": "对应评分维度",
    "场景价值与行业可复制性": "场景价值与行业可复制性",
    "25%": "25%",

    # ---- Slide 5: 第一章内容 ----
    "建议覆盖目标用户与核心痛点、真实场景、可量化的价值收益、行业可复制性，以及你的创新点与差异化优势。": (
        "边缘 AI 运维 4 大痛点：千级节点 · 数十模型 · 4 类漂移 · 风险分级模糊。"
        "我们的方案：4 Agent 协同 + 7 决策 Skill + HITL seam。"
        "可迁移到制造 / 零售 / 物流等任何边缘 AI 场景。"
    ),
    "（示例）": "目标用户：边缘 AI 运维团队 · 模型平台 SRE · OTA 平台负责人",

    # ---- Slide 6: 第二章扉页 ----
    "第二章": "第二章",
    "方案总览": "方案总览",

    # ---- Slide 7: 第二章内容 ----
    "第二章 · 承上启下": "第二章 · 承上启下",
    "建议用一张架构图呈现整体方案，说明端到端主流程和关键技术选型的必要性。": (
        "EdgeSentinel（检测）→ EdgeDiagnostician（归因）→ "
        "EdgeOrchestrator（规划）→ EdgeSentry（验证）"
        "→ Request Queue（HITL seam）→ External Operator Pool（生产环境外）"
    ),

    # ---- Slide 8: 第三章扉页 ----
    "第三章": "第三章",
    "多 Agent 协同设计": "多 Agent 协同设计",
    "多 Agent 协同与自主闭环能力": "多 Agent 协同与自主闭环能力",

    # ---- Slide 9: 第三章内容 ----
    "建议覆盖 Agent 分工、任务拆解、上下文传递与状态流转、异常与冲突处理，以及高风险动作的安全边界。": (
        "分工：4 Agent 各管一阶段。任务拆解：dependency_graph 显式声明。"
        "上下文：每个 Agent 输出 JSON 契约 + evidence_refs。"
        "异常：risk-guard L0-L3 分级；冲突：top_candidate + alternatives + confidence。"
        "安全边界：L2/L3 必经 HITL，rollback_point + 队列审计。"
    ),

    # ---- Slide 10: 第四章扉页 ----
    "第四章": "第四章",
    "Skill 工程体系": "Skill 工程体系",
    "Skill 工程体系与生态复用": "Skill 工程体系与生态复用",

    # ---- Slide 11: 第四章内容 ----
    "第四章 · 本赛题必选项": "第四章 · 本赛题必选项",
    "建议覆盖 Skill 清单与任务覆盖、单个 Skill 的规格（输入输出/依赖/失败处理）、复用性、生命周期管理，以及对官方 Skills 的复用。": (
        "7 个决策类 Skill：alert-fusion · impact-mapping · log-trace-rca · "
        "model-governance · remediation-plan · risk-guard · recovery-verify。"
        "每个含 YAML frontmatter（version + maturity）+ Inputs + Procedure + "
        "Output Contract + Quality Gates。"
        "复用：可迁移到任何 AIOps 场景；版本化 frontmatter 支持生命周期管理。"
        "官方 Skills：Edge AIOps 不强依赖云产品，但接口与阿里云 MCP 适配层对齐，未来可接入。"
    ),

    # ---- Slide 12: 第五章扉页 ----
    "第五章": "第五章",
    "工程落地、运行验证与安全可审计": "工程落地、运行验证与安全可审计",
    "工程落地与安全可审计": "工程落地与安全可审计",
    "20%": "20%",

    # ---- Slide 13: 第五章内容 ----
    "建议覆盖可运行性、运行证据、可观测与检索链路、安全治理机制，以及云产品选型的必要性与边界。": (
        "可运行：mock_tool_server.py 已跑通，5 类 curl 输出见 docs/demo-run-evidence.md。"
        "证据：trace + requests 端点全审计，每个 Agent 输出含 evidence_refs。"
        "可观测：tool trace + request queue + LoongSuite OTel（复赛）。"
        "检索：mock_runbook 轻量 RAG（tag + symptom 评分），返回 score=6.0 + breakdown。"
        "安全：L0/L1 auto_approved vs L2/L3 pending_approval；approval ticket；rollback_point；audit。"
        "云产品：Edge AIOps 主要信号源在边缘 + 模型 + OTA，未来可接 ARMS / PAI / SLS / Nacos。"
    ),

    # ---- Slide 14: 第六章扉页 ----
    "第六章": "第六章",
    "开放 / 开源计划": "开放 / 开源计划",
    "开放 / 开源贡献": "开放 / 开源贡献",
    "5%": "5%",

    # ---- Slide 15: 第六章内容 ----
    "建议覆盖可复用成果、接口契约与文档示例，以及开源协议与第三方依赖。": (
        "可复用成果：完整 demo 仓库（含 6 Worker + 4 Agent + 7 Skill + 11 工具 + 2 场景）。"
        "接口契约：tool_catalog.json 标 future_mcp_mapping，mock 与真协议 1:1 对齐。"
        "文档：README + at/* + docs/* 共 8 份。"
        "开源协议：Apache-2.0。第三方依赖：仅 stdlib（mock 阶段）。"
        "PR 计划：5 个（AgentTeams docs + Skill template + MCP server + AgentScope OTel + Argo RBAC）。"
    ),

    # ---- Slide 16: 第七章扉页 ----
    "第七章 · 对应「当前进展」与整体可行性": "第七章 · 对应「当前进展」与整体可行性",
    "落地计划与进展": "落地计划与进展",

    # ---- Slide 17: 第七章内容 ----
    "建议覆盖当前进展、里程碑与落地计划，以及风险控制。": (
        "当前进展：v0.3.0 demo 跑通（4 Agent + 7 Skill + 11 工具 + 2 场景 + mock 验证）。"
        "Week 1：K3s + Triton + Prometheus + Grafana。"
        "Week 2：MLflow + Argo Rollouts + OTel + Jaeger + 5 个 Operator。"
        "Week 3：RAG + LoongSuite OTel + 全链路演练。"
        "Week 4：失败注入 + RBAC 验证 + evidence URL + 录屏。"
        "风险：LLM 限速 / K3s 故障 / Argo RBAC / MLflow stage 竞争 / LLM 幻觉。"
        "缓解：预录 fallback / docker-compose 备份 / RBAC 脚本 / 幂等 Operator / evidence 闸。"
    ),

    # ---- Slide 18: 第八章扉页 ----
    "第八章 ·": "第八章 ·",
    "团队介绍": "团队介绍",

    # ---- Slide 19: 第八章内容 ----
    "第八章": "第八章",
}


def replace_in_text_frame(text_frame, mapping: Dict[str, str]) -> bool:
    """Replace text in every paragraph by joining into a single string match.

    Returns True if any replacement happened.
    """
    changed = False
    for paragraph in text_frame.paragraphs:
        original = paragraph.text
        if not original:
            continue
        joined = original.strip()
        if joined in mapping:
            # Replace whole paragraph text but preserve font from first run if present.
            runs = paragraph.runs
            if runs:
                runs[0].text = mapping[joined]
                for run in runs[1:]:
                    run.text = ""
            else:
                run = paragraph.add_run()
                run.text = mapping[joined]
            changed = True
    return changed


def edit_template(template_path: Path, output_path: Path) -> int:
    prs = Presentation(str(template_path))
    total_replaced = 0
    for slide_idx, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if shape.has_text_frame:
                if replace_in_text_frame(shape.text_frame, REPLACEMENTS):
                    total_replaced += 1
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        if cell.text_frame:
                            if replace_in_text_frame(cell.text_frame, REPLACEMENTS):
                                total_replaced += 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    return total_replaced


def main() -> None:
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE}")
    n = edit_template(TEMPLATE, OUTPUT)
    print(f"Template: {TEMPLATE}")
    print(f"Output:   {OUTPUT}")
    print(f"Replacements applied: {n} text frame(s)")


if __name__ == "__main__":
    main()
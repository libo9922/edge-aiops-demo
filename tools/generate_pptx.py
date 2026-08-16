"""Generate Edge AIOps submission PPTX using the OpsPilot reference as template.

Strategy:
  1. Load `/workspace/OpsPilot-Zero-AgentTeams-初赛方案.pptx`
  2. Strip all PICTURE shapes (and their media files) so the deck is text-only
  3. Replace placeholder text with our content
  4. Fill team info into slides 18-19
  5. Save to `docs/edge-aiops-submission.pptx`

This preserves all decorative auto-shapes (rounded boxes, accent lines, layout)
while removing architecture screenshots.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Dict, Tuple

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from lxml import etree


REF_PPTX = Path("/workspace/OpsPilot-Zero-AgentTeams-初赛方案.pptx")
WORK_DIR = Path("/tmp/edge_aiops_pptx_build")
OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "edge-aiops-submission.pptx"


# ----------------------------------------------------------------------
# Text replacements (slide-by-slide, after stripping pictures)
# ----------------------------------------------------------------------

REPLACEMENTS: Dict[str, str] = {
    # ---- Slide 1: Cover ----
    "OpsPilot Zero": "Edge AIOps",
    "AgentTeams 智能运维": "Multi-Agent Incident Response",
    "多 Agent + Skill 驱动的故障自愈闭环": "Agents Decide · Operators Execute",
    "GOAI 2026 · Agent Infra 新智基座": "Agent Infra 新智基座 · 2026",
    "吉林大学 · 大数据管理与应用 · 个人团队": "吉林大学 · 大数据管理与应用 · 个人团队",

    # ---- Slide 2: P0 一页纸速览 ----
    "项目名称": "项目名称",
    "OpsPilot Zero\n智能运维 AgentTeam": "Edge AIOps\n边缘 + 模型 + OTA 智能运维",

    "问题与场景": "问题与场景",
    "面向云上应用 / SRE 团队\n故障需人工翻日志、查 Trace、审配置\n恢复慢且依赖资深经验": (
        "面向边缘 AI / SRE 团队\n事故需人工翻日志、查 Trace、审配置\nOTA 回归靠资深经验恢复\n千级节点 + 数十模型 + 4 类漂移"
    ),

    "核心解决方案": "核心解决方案",
    "多 Agent + Skill + 工具网关\n告警→根因→修复→验证 零人工闭环\n低风险自动执行，高风险审批": (
        "4 职能 Agent + 7 决策 Skill + 工具网关\n检测→归因→规划→验证 零人工闭环\nagents-decide / operators-execute\nHITL seam 做 L2/L3 审批"
    ),

    "创新点与差异化": "创新点与差异化",
    "4 个 LLM Agent + TeamLeader\n主动跨系统取证\n内置 L0-L3 风险分级": (
        "4 LLM Agent + TeamLeader + Manager\n主动跨系统取证\n内置 L0-L3 风险分级\nmock 与真协议 1:1 对齐"
    ),

    "开放 / 复用价值": "开放 / 复用价值",
    "7 个 Skill + 8 类工具契约\n可发布到 Nacos AI Registry\n平滑升级 MCP / Higress": (
        "7 Skill + 11 mock 工具契约\n可发布到 Nacos AI Registry\n平滑升级 MCP / Higress\nApache-2.0 协议"
    ),

    "当前进展": "当前进展",
    "2 个生产事故闭环：\n连接池耗尽 + 慢 SQL 劣化\n结构化事故报告": (
        "2 个 Edge AIOps 事故闭环：\nOTA 模型回归 + 边缘节点故障\n结构化事故报告 + 4 周落地 roadmap"
    ),

    # ---- Slide 5: 第一章内容 ----
    "01 · 场景与价值": "01 · 场景与价值",
    "两个事故场景 · 一个方案": "边缘 + 模型 + OTA · 一个协同方案",
    "场景 01 · INC-1001": "场景 01 · INC-2001",
    "连接池耗尽": "OTA 模型回归",
    "Nacos 变更 db.pool.maxSize 50→8\n订单 p99 高达 6800ms / 5xx 18.4%\n\nAgent 自动：归并告警 → 定位根因\n→ 回滚配置 → 验证恢复\n\n结果：p99 420ms / 5xx 0.3%": (
        "OTA 把 resnet50 v3.2.1 推到杭州集群（无 canary）\naccuracy 0.92 → 0.71 / p99 420 → 1450ms\n\n"
        "Agent 自动：归并告警 → 多源归因\n→ quarantine_node L1 + rollback_model L2 待审\n\n"
        "结果：accuracy 0.91 / p99 420ms / fleet healthy"
    ),
    "场景 02 · INC-1002": "场景 02 · INC-2002",
    "慢 SQL 劣化": "边缘节点故障",
    "新索引误建，5xx 飙至 18.4%\n慢 SQL 列表 + 执行计划取证\n\nAgent 自动：定位慢 SQL\n→ DROP INDEX 回滚\n→ 验证恢复\n\n结果：10 分钟内 5xx → 0.3%": (
        "edge-shanghai-02 不可达 + edge-shanghai-05 GPU 热临界\n"
        "throughput 12 qps / latency 1850ms\n\n"
        "Agent 自动：多源归因 → quarantine_node + throttle\n"
        "→ verify 端点恢复 + throughput 恢复\n\n"
        "结果：fleet healthy / SLO 达标"
    ),
    "6800→420\nms": "0.71→0.91\nratio",
    "p99 响应": "accuracy",
    "18.4→0.3\n%": "0.34→0.10\nscore",
    "5xx 错误率": "drift score",
    "<10\n分钟": "≤12\n分钟",
    "平均修复时长": "端到端闭环",
    # single-paragraph variants
    "6800→420": "0.71→0.91",
    "ms": "ratio",
    "p99 响应": "accuracy",
    "18.4→0.3": "0.34→0.10",
    "5xx 错误率": "drift score",
    "<10": "≤12",
    "分钟": "分钟",
    "平均修复时长": "端到端闭环",
    "%": "score",
    "Nacos 变更 db.pool.maxSize 50→8\n订单 p99 高达 6800ms / 5xx 18.4%\n\nAgent 自动：归并告警 → 定位根因\n→ 回滚配置 → 验证恢复\n\n结果：p99 420ms / 5xx 0.3%": (
        "OTA 把 resnet50 v3.2.1 推到杭州集群（无 canary）\n"
        "accuracy 0.92 → 0.71 / p99 420 → 1450ms\n\n"
        "Agent 自动：归并告警 → 多源归因\n→ quarantine_node L1 + rollback_model L2 待审\n\n"
        "结果：accuracy 0.91 / p99 420ms / fleet healthy"
    ),
    "新索引误建，5xx 飙至 18.4%\n慢 SQL 列表 + 执行计划取证\n\nAgent 自动：定位慢 SQL\n→ DROP INDEX 回滚\n→ 验证恢复\n\n结果：10 分钟内 5xx → 0.3%": (
        "edge-shanghai-02 不可达 + edge-shanghai-05 GPU 热临界\n"
        "throughput 12 qps / latency 1850ms\n\n"
        "Agent 自动：多源归因 → quarantine_node + throttle\n"
        "→ verify 端点恢复 + throughput 恢复\n\n"
        "结果：fleet healthy / SLO 达标"
    ),
    # Slide 5 single-paragraph fragments
    "Nacos 变更 db.pool.maxSize 50→8": "OTA 把 resnet50 v3.2.1 推到杭州集群（无 canary）",
    "订单 p99 高达 6800ms / 5xx 18.4%": "accuracy 0.92 → 0.71 / p99 420 → 1450ms",
    "Agent 自动：归并告警 → 定位根因": "Agent 自动：归并告警 → 多源归因",
    "→ 回滚配置 → 验证恢复": "→ quarantine_node L1 + rollback_model L2 待审",
    "结果：p99 420ms / 5xx 0.3%": "结果：accuracy 0.91 / p99 420ms / fleet healthy",
    "新索引误建，5xx 飙至 18.4%": "edge-shanghai-02 不可达 + edge-shanghai-05 GPU 热临界",
    "慢 SQL 列表 + 执行计划取证": "throughput 12 qps / latency 1850ms",
    "Agent 自动：定位慢 SQL": "Agent 自动：多源归因",
    "→ DROP INDEX 回滚": "→ quarantine_node + throttle",
    "→ 验证恢复": "→ verify 端点恢复",
    "结果：10 分钟内 5xx → 0.3%": "结果：fleet healthy / SLO 达标",

    # ---- Slide 7: 第二章内容 ----
    "02 · 方案总览": "02 · 方案总览",
    "端到端 6 阶段流程": "端到端 4 阶段流程 + HITL seam",

    # ---- Slide 9: 第三章内容 ----
    "03 · 多 Agent 协同": "03 · 多 Agent 协同",
    "5 个角色，1 个 TeamLeader": "4 业务 Agent + 1 TeamLeader + 1 Manager",
    "LEAD": "LEAD",
    "TeamLeader": "TeamLeader",
    "调度中枢": "调度中枢",
    "统一编排\n串行协作\n逐级交付": "统一编排\nManager 动态调度\nDAG-ready workflow",
    "Alert Intake": "EdgeSentinel",
    "告警入口": "边缘哨兵",
    "原始告警\n归并降噪\n输出事件": "边缘+模型+OTA\n三信号融合\n输出事故候选",
    "RCA Analyst": "EdgeDiagnostician",
    "根因分析": "边缘诊断师",
    "日志/Trace\n指标/配置\n跨系统取证": "日志+Trace+OTA\n模型遥测+Runbook RAG\n多源归因",
    "Remediation": "EdgeOrchestrator",
    "修复规划": "边缘编排师",
    "生成方案\nL0-L3 分级\n高危走审批": "发执行请求\nL0-L3 分级\nHITL seam",
    "Verify": "EdgeSentry",
    "恢复验证": "边缘验收师",
    "检查指标\n自动验证\n输出报告": "SLA + 队列状态\nrequest verification\npostmortem",
    "原始告警\n归并降噪\n输出事件": "边缘+模型+OTA\n三信号融合\n输出事故候选",
    "日志/Trace\n指标/配置\n跨系统取证": "日志+Trace+OTA\n模型遥测+Runbook RAG\n多源归因",
    "生成方案\nL0-L3 分级\n高危走审批": "发执行请求\nL0-L3 分级\nHITL seam",
    "统一编排\n串行协作\n逐级交付": "统一编排\nManager 动态调度\nDAG-ready workflow",
    # single-paragraph variants
    "原始告警": "边缘+模型+OTA",
    "归并降噪": "三信号融合",
    "输出事件": "输出事故候选",
    "日志/Trace": "日志+Trace+OTA",
    "指标/配置": "模型遥测+Runbook RAG",
    "跨系统取证": "多源归因",
    "串行协作": "Manager 动态调度",
    "逐级交付": "DAG-ready workflow",
    "L0-L3 分级": "L0-L3 分级",
    "高危走审批": "HITL seam",
    "检查指标": "SLA + 队列状态",
    "自动验证": "request verification",
    "输出报告": "postmortem",
    "告警入口": "边缘哨兵",
    "根因分析": "边缘诊断师",
    "修复规划": "边缘编排师",
    "恢复验证": "边缘验收师",
    "原始告警\n归并降噪\n输出事件\n": "边缘+模型+OTA\n三信号融合\n输出事故候选\n",
    "生成方案\nL0-L3 分级\n高危走审批\n": "发执行请求\nL0-L3 分级\nHITL seam\n",

    # ---- Slide 11: 第四章内容 ----
    "04 · Skill 体系": "04 · Skill 体系",
    "7 个 Skill · 1 个示例规格": "7 个决策类 Skill · 1 个示例规格",
    "alert-fusion": "alert-fusion",
    "归并": "告警融合",
    "event-enrich": "impact-mapping",
    "补全": "影响映射",
    "rca-tree": "log-trace-rca",
    "根因": "多源归因",
    "remediation-plan": "remediation-plan",
    "规划": "修复计划",
    "auto-executor": "risk-guard",
    "执行": "风险分级",
    "recovery-verify": "recovery-verify",
    "验证": "恢复验收",
    "★ risk-guard 完整规格": "★ risk-guard 完整规格",
    "05 · 工程落地、运行验证与安全可审计": "05 · 工程落地、运行验证与安全可审计",
    "8 类工具 · 4 道安全闸": "11 类工具 · 4 道安全闸",
    "8 类工具契约": "11 类工具契约",
    "可运行 · 可观测 · 可审计": "mock 跑通 · 全审计 · 接口稳定",
    "风险守卫（执行前强制调用）": "风险守卫（L0-L3 分级）",
    "其余 6 个 Skill 契约": "其余 6 个 Skill 契约",
    "· alert-fusion: 原始告警 → 归并事件": "· alert-fusion: 多类信号 → 事故候选",
    "· event-enrich: 事件 → 补全上下文": "· impact-mapping: 事故 → 节点+SLO 影响",
    "· rca-tree: 事件 → 候选根因树": "· log-trace-rca: 多源证据 → top_candidate",
    "· remediation-plan: 根因 → 方案+风险": "· remediation-plan: RCA → 风险分级方案",
    "· auto-executor: 方案 → 执行结果": "· model-governance: 模型回归/漂移分类",
    "· recovery-verify: 动作 → 验证指标": "· recovery-verify: SLA + 队列状态验证",
    "守卫": "风险分级",
    "恢复验收\nrecovery-verify\n自动检查 5xx / p99\n未通过自动回滚": "恢复验收\nrecovery-verify\n自动检查 accuracy / p99\n未通过自动回滚",

    # ---- Slide 13: 第五章内容 ----
    "05 · 工程落地、运行验证与安全可审计": "05 · 工程落地、运行验证与安全可审计",
    "可运行 · 可观测 · 可审计": "mock 跑通 · 全审计 · 接口稳定",

    # ---- Slide 15: 第六章内容 ----
    "06 · 开源开放计划": "06 · 开源开放计划",
    "5 个 PR 目标 · Apache-2.0 协议": "5 个 PR 目标 · Apache-2.0",
    "仓库 opspilot-zero-demo": "仓库 edge-aiops-demo",
    "8 类工具 HTTP 接口": "11 mock 工具 HTTP 接口",
    "8 类工具": "11 类工具",
    "7 个 Skill + 8 类工具契约": "7 个 Skill + 11 类工具契约",

    # ---- Slide 17: 第七章内容 ----
    "07 · 落地计划与进展": "07 · 落地计划与进展",
    "Demo 已跑通 · 4 周 roadmap 已规划": "v0.3.0 demo 已跑通 · 4 周 final-roadmap 已规划",
    "INC-1001 / INC-1002": "INC-2001 / INC-2002",

    # ---- Slide 18: 团队扉页 ----
    "08": "08",
    "第 八 章": "第 八 章",
    "团队介绍": "团队介绍",
    "Team": "Team",
    "个人团队": "个人团队",
    "吉林大学": "吉林大学",
    "AIOps": "AIOps",
    "LLM Agent": "LLM Agent",
    "MCP 生态": "MCP 生态",
    "全栈": "全栈",
    "个人团队 · 吉林大学 · 大数据管理与应用": "个人团队 · 吉林大学 · 大数据管理与应用",

    # ---- Slide 19: 团队详情 ----
    "08 · 团队介绍": "08 · 团队介绍",
    "个人团队 · 一个人就是一支队伍": "个人团队 · 一个人就是一支队伍",
    "OpsPilot Zero": "Edge AIOps",
    "─── 个人团队 · 1 人": "─── 个人团队 · 1 人",
    "学校": "学校",
    "专业": "专业",
    "大数据管理与应用（本科）": "大数据管理与应用（本科）",
    "方向": "方向",
    "AIOps · LLM Agent · MCP 生态": "AIOps · LLM Agent · MCP 生态 · Edge AI",
    "负责": "负责",
    "方案 · Demo · PPT · 文档": "方案 · Demo · PPT · 文档 · Skill 体系",
    "技术栈": "技术栈",
    "Python": "Python",
    "FastAPI": "FastAPI",
    "LLM": "LLM",
    "Nacos": "Nacos",
    "MCP": "MCP",
    "Docker": "Docker",
    "项目产出": "项目产出",
    "· opspilot-zero-demo 最小可运行仓库": "· edge-aiops-demo 完整仓库",
    "· 2 个生产事故的端到端 Demo": "· 2 个 Edge AIOps 事故的端到端 Demo",
    "· 7 个 Skill + 8 类工具契约": "· 7 个 Skill + 11 类工具契约",
    "· 结构化事故报告模板": "· 结构化事故报告模板 · 4 周落地 roadmap",
}


def strip_pictures_from_xml(slide_xml_path: Path) -> int:
    """Remove all <p:pic> elements from a slide XML; return removed count."""
    tree = etree.parse(str(slide_xml_path))
    nsmap = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
    pics = tree.findall(".//p:pic", nsmap)
    count = len(pics)
    for pic in pics:
        parent = pic.getparent()
        if parent is not None:
            parent.remove(pic)
    tree.write(str(slide_xml_path), xml_declaration=True, encoding="UTF-8", standalone=True)
    return count


def replace_in_text_frame(text_frame, mapping: Dict[str, str]) -> int:
    """Replace text in each paragraph whose stripped text matches a key.

    Returns count of replacements.
    """
    n = 0
    for paragraph in text_frame.paragraphs:
        original = paragraph.text.strip()
        if not original or original not in mapping:
            continue
        new_text = mapping[original]
        runs = paragraph.runs
        if runs:
            runs[0].text = new_text
            for run in runs[1:]:
                run.text = ""
        else:
            run = paragraph.add_run()
            run.text = new_text
        n += 1
    return n


def extract_pptx(pptx_path: Path, work_dir: Path) -> None:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)
    with zipfile.ZipFile(pptx_path, "r") as zf:
        zf.extractall(work_dir)


def repack_pptx(work_dir: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(work_dir.rglob("*")):
            if path.is_file():
                arcname = path.relative_to(work_dir).as_posix()
                zf.write(str(path), arcname)


def main() -> None:
    if not REF_PPTX.exists():
        raise FileNotFoundError(f"Reference PPTX not found: {REF_PPTX}")

    extract_pptx(REF_PPTX, WORK_DIR)

    # 1) Strip <p:pic> from every slide XML
    slides_dir = WORK_DIR / "ppt" / "slides"
    total_pics = 0
    for slide_xml in sorted(slides_dir.glob("slide*.xml")):
        total_pics += strip_pictures_from_xml(slide_xml)

    # 2) Drop media files (orphan images referenced by no shape)
    media_dir = WORK_DIR / "ppt" / "media"
    if media_dir.exists():
        for media_file in media_dir.iterdir():
            media_file.unlink()
        media_dir.rmdir()

    # 3) Strip picture relationships from each slide's .rels file
    rels_dir = WORK_DIR / "ppt" / "slides" / "_rels"
    for rels_xml in sorted(rels_dir.glob("slide*.xml.rels")):
        tree = etree.parse(str(rels_xml))
        ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
        # Remove Image relationships
        for rel in tree.findall("r:Relationship", ns):
            t = rel.get("Type", "")
            if "image" in t.lower():
                parent = rel.getparent()
                if parent is not None:
                    parent.remove(rel)
        tree.write(str(rels_xml), xml_declaration=True, encoding="UTF-8", standalone=True)

    # 4) Repack to a temp pptx, open with python-pptx, do text replacements, save
    intermediate = WORK_DIR / "intermediate.pptx"
    repack_pptx(WORK_DIR, intermediate)

    prs = Presentation(str(intermediate))
    total_text_replacements = 0
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                total_text_replacements += replace_in_text_frame(shape.text_frame, REPLACEMENTS)
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        if cell.text_frame:
                            total_text_replacements += replace_in_text_frame(cell.text_frame, REPLACEMENTS)

    prs.save(str(OUTPUT))

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"Reference: {REF_PPTX}")
    print(f"Output:    {OUTPUT}")
    print(f"Pictures stripped: {total_pics}")
    print(f"Text replacements: {total_text_replacements}")
    print(f"Output size: {size_kb:.1f} KB (vs 137 MB original)")


if __name__ == "__main__":
    main()
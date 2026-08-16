from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = PROJECT_ROOT / "scenarios"


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_scenarios() -> List[str]:
    return sorted(path.stem for path in SCENARIO_DIR.glob("*.json"))


def load_scenario(scenario_id: str) -> Dict[str, Any]:
    path = SCENARIO_DIR / f"{scenario_id}.json"
    if not path.exists():
        available = ", ".join(list_scenarios())
        raise ValueError(f"Unknown scenario '{scenario_id}'. Available: {available}")
    return load_json(path)


def compact(value: Any, max_len: int = 180) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


class BaseMockTools:
    def __init__(self, scenario_id: str) -> None:
        self.scenario_id = scenario_id
        self.requests: List[Dict[str, Any]] = []
        self.trace: List[Dict[str, Any]] = []

    def _record(self, tool: str, args: Dict[str, Any], result: Any) -> Any:
        self.trace.append(
            {
                "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "tool": tool,
                "args": args,
                "result_preview": compact(result),
            }
        )
        return result

    def reset(self) -> None:
        self.requests.clear()
        self.trace.clear()

    # ---------- decision-support (read-only) ----------
    def get_customer_complaint(self) -> Dict[str, Any]:
        raise NotImplementedError

    def list_alerts(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def query_metrics(self, phase: str = "before") -> Dict[str, Any]:
        raise NotImplementedError

    def search_logs(self, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def query_traces(self, endpoint: Optional[str] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def list_nodes(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_version_history(self, model_name: Optional[str] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def list_recent_updates(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_resource_snapshot(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def search_runbooks(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def check_inference_endpoint(self, endpoint: str) -> Dict[str, Any]:
        raise NotImplementedError

    # ---------- execution-request (does NOT execute; only files a request) ----------
    def create_action_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def get_action_request(self, request_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def create_approval_task(self, title: str, details: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class LocalMockTools(BaseMockTools):
    def __init__(self, scenario_id: str) -> None:
        super().__init__(scenario_id)
        self.scenario = load_scenario(scenario_id)
        self._next_request_id = 1

    def _scenario(self, key: str, default: Any) -> Any:
        return self.scenario.get(key, default)

    # ---------- read-only ----------
    def get_customer_complaint(self) -> Dict[str, Any]:
        return self._record("mock_ticket.get_customer_complaint", {}, self.scenario["complaint"])

    def list_alerts(self) -> List[Dict[str, Any]]:
        return self._record("mock_monitoring.list_alerts", {}, self._scenario("alerts", []))

    def query_metrics(self, phase: str = "before") -> Dict[str, Any]:
        metrics = self.scenario["metrics"]
        # If at least one L0/L1 request was auto-approved in mock, surface improved metrics.
        approved_l1 = any(r.get("status") == "auto_approved" for r in self.requests)
        if phase == "after" and approved_l1:
            selected = metrics.get("after_expected", metrics["before"])
        else:
            selected = metrics["before"]
        return self._record("mock_monitoring.query_metrics", {"phase": phase}, selected)

    def search_logs(self, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        logs = self._scenario("logs", [])
        if keyword:
            lowered = keyword.lower()
            logs = [row for row in logs if lowered in row.get("message", "").lower()]
        return self._record("mock_logs.search_logs", {"keyword": keyword}, logs)

    def query_traces(self, endpoint: Optional[str] = None) -> List[Dict[str, Any]]:
        traces = self._scenario("traces", [])
        if endpoint:
            traces = [row for row in traces if row.get("endpoint") == endpoint]
        return self._record("mock_traces.query_traces", {"endpoint": endpoint}, traces)

    def list_nodes(self) -> List[Dict[str, Any]]:
        return self._record("mock_fleet.list_nodes", {}, self._scenario("fleet", {}).get("nodes", []))

    def get_version_history(self, model_name: Optional[str] = None) -> List[Dict[str, Any]]:
        versions = self._scenario("model_versions", [])
        if model_name:
            versions = [v for v in versions if v.get("model") == model_name]
        return self._record("mock_model.get_version_history", {"model": model_name}, versions)

    def list_recent_updates(self) -> List[Dict[str, Any]]:
        return self._record("mock_ota.list_recent_updates", {}, self._scenario("ota_history", []))

    def get_resource_snapshot(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        snapshots = self._scenario("node_snapshots", [])
        if node_id:
            snapshots = [s for s in snapshots if s.get("node_id") == node_id]
        return self._record("mock_node.get_resource_snapshot", {"node_id": node_id}, snapshots)

    def search_runbooks(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lightweight Runbook RAG (demo-stage). See docs/lightweight-rag-design.md.

        Algorithm: keyword filter + tag overlap score * 2 + symptom overlap * 1.5
        + title substring match * 1. Returns top-K=3 sorted by score.
        """
        runbooks = self._scenario("runbooks", [])
        if not query:
            return self._record("mock_runbook.search", {"query": query}, runbooks)

        tokens = [t for t in query.lower().split() if len(t) >= 2]
        scored: List[Dict[str, Any]] = []
        for row in runbooks:
            tags = {t.lower() for t in row.get("tags", [])}
            symptoms = {s.lower() for s in row.get("symptoms", [])}
            match_terms = {t.lower() for t in row.get("match_terms", [])}
            title = row.get("title", "").lower()

            tag_overlap = sum(1 for t in tokens if t in tags)
            symptom_overlap = sum(1 for t in tokens if t in symptoms)
            term_overlap = sum(1 for t in tokens if any(t in mt for mt in match_terms))
            title_match = 1 if any(t in title for t in tokens) else 0

            score = tag_overlap * 2.0 + symptom_overlap * 1.5 + term_overlap * 1.0 + title_match * 1.0
            if score > 0:
                enriched = dict(row)
                enriched["score"] = round(score, 2)
                enriched["score_breakdown"] = {
                    "tag_overlap": tag_overlap,
                    "symptom_overlap": symptom_overlap,
                    "term_overlap": term_overlap,
                    "title_match": title_match,
                }
                scored.append(enriched)

        scored.sort(key=lambda r: r["score"], reverse=True)
        top_k = scored[:3]
        return self._record("mock_runbook.search", {"query": query}, top_k)

    def check_inference_endpoint(self, endpoint: str) -> Dict[str, Any]:
        metrics = self.query_metrics("after" if any(r.get("status") == "auto_approved" for r in self.requests) else "before")
        accuracy = metrics.get("inference_accuracy", 0)
        latency = metrics.get("p99_latency_ms", 9999)
        ok = any(r.get("status") == "auto_approved" for r in self.requests) and accuracy >= 0.88 and latency <= 800
        result = {
            "endpoint": endpoint,
            "status": "ok" if ok else "degraded",
            "inference_accuracy": accuracy,
            "p99_latency_ms": latency,
            "message": "Synthetic inference probe passed." if ok else "Synthetic probe still sees degradation.",
        }
        return self._record("mock_probe.check_inference_endpoint", {"endpoint": endpoint}, result)

    # ---------- execution-request (mock: file a request, do not actually execute) ----------
    def create_action_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """File an execution request. Does NOT execute.

        Real production wiring: an external Operator (K8s / ML platform / OTA)
        polls this request queue, performs the action, and updates status.
        Mock here just records the request and applies the policy gate:
        L0/L1 → auto_approved; L2/L3 → pending_approval.
        """
        risk_level = request.get("risk_level", "L1")
        status = "auto_approved" if risk_level in ("L0", "L1") else "pending_approval"
        record = {
            "request_id": f"REQ-{self.scenario_id.upper()}-{self._next_request_id:03d}",
            "action_type": request.get("action_type"),
            "target": request.get("target"),
            "parameters": request.get("parameters", {}),
            "risk_level": risk_level,
            "status": status,
            "submitted_by": request.get("submitted_by", "edge_orchestrator"),
            "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "approver_required_for": [] if status == "auto_approved" else ["L2/L3 approver"],
        }
        self._next_request_id += 1
        self.requests.append(record)
        return self._record("mock_executor.create_action_request", request, record)

    def get_action_request(self, request_id: str) -> Dict[str, Any]:
        record = next((r for r in self.requests if r["request_id"] == request_id), None)
        if record is None:
            return {"ok": False, "error": f"unknown request_id {request_id}"}
        return self._record("mock_executor.get_action_request", {"request_id": request_id}, record)

    def create_approval_task(self, title: str, details: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "status": "created",
            "ticket_id": f"APPROVAL-{self.scenario_id.upper()}",
            "title": title,
            "details": details,
        }
        return self._record("mock_ticket.create_approval_task", {"title": title}, result)


def max_severity(alerts: Iterable[Dict[str, Any]]) -> str:
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    severities = [alert.get("severity", "P4") for alert in alerts]
    return min(severities, key=lambda item: order.get(item, 99), default="P4")
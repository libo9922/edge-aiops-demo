from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict
from urllib.parse import unquote, urlparse

from mock_tools import LocalMockTools, list_scenarios


TOOL_STATES: Dict[str, LocalMockTools] = {}


def get_state(scenario_id: str) -> LocalMockTools:
    if scenario_id not in TOOL_STATES:
        TOOL_STATES[scenario_id] = LocalMockTools(scenario_id)
    return TOOL_STATES[scenario_id]


def reset_state(scenario_id: str) -> Dict[str, Any]:
    TOOL_STATES[scenario_id] = LocalMockTools(scenario_id)
    return {"scenario_id": scenario_id, "status": "reset"}


def call_tool(tools: LocalMockTools, name: str, payload: Dict[str, Any]) -> Any:
    handlers: Dict[str, Callable[[], Any]] = {
        # decision-support (read-only)
        "mock_ticket.get_customer_complaint": lambda: tools.get_customer_complaint(),
        "mock_monitoring.list_alerts": lambda: tools.list_alerts(),
        "mock_monitoring.query_metrics": lambda: tools.query_metrics(payload.get("phase", "before")),
        "mock_logs.search_logs": lambda: tools.search_logs(payload.get("keyword")),
        "mock_traces.query_traces": lambda: tools.query_traces(payload.get("endpoint")),
        "mock_fleet.list_nodes": lambda: tools.list_nodes(),
        "mock_model.get_version_history": lambda: tools.get_version_history(payload.get("model")),
        "mock_ota.list_recent_updates": lambda: tools.list_recent_updates(),
        "mock_node.get_resource_snapshot": lambda: tools.get_resource_snapshot(payload.get("node_id")),
        "mock_runbook.search": lambda: tools.search_runbooks(payload.get("query")),
        "mock_probe.check_inference_endpoint": lambda: tools.check_inference_endpoint(payload["endpoint"]),
        # execution-request (files a request; does NOT execute)
        "mock_executor.create_action_request": lambda: tools.create_action_request(payload.get("request", payload)),
        "mock_executor.get_action_request": lambda: tools.get_action_request(payload["request_id"]),
        "mock_ticket.create_approval_task": lambda: tools.create_approval_task(payload["title"], payload.get("details", {})),
    }
    if name not in handlers:
        available = ", ".join(sorted(handlers))
        raise ValueError(f"unknown tool call '{name}', available: {available}")
    return handlers[name]()


class MockToolHandler(BaseHTTPRequestHandler):
    server_version = "EdgeAIOpsMockToolGateway/0.1"

    def _send(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
        try:
            if parts == ["health"]:
                self._send(HTTPStatus.OK, {"ok": True, "service": "edge-aiops-mock-tool-gateway"})
                return
            if parts == ["scenarios"]:
                self._send(HTTPStatus.OK, {"ok": True, "result": list_scenarios()})
                return
            if len(parts) == 3 and parts[0] == "tools" and parts[2] == "trace":
                tools = get_state(parts[1])
                self._send(HTTPStatus.OK, {"ok": True, "result": tools.trace})
                return
            if len(parts) == 3 and parts[0] == "tools" and parts[2] == "requests":
                tools = get_state(parts[1])
                self._send(HTTPStatus.OK, {"ok": True, "result": tools.requests})
                return
            self._send(HTTPStatus.NOT_FOUND, {"ok": False, "error": "unknown endpoint"})
        except Exception as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
        try:
            if len(parts) != 3 or parts[0] != "tools":
                self._send(HTTPStatus.NOT_FOUND, {"ok": False, "error": "expected /tools/{scenario_id}/{tool_call}"})
                return
            scenario_id, tool_call = parts[1], parts[2]
            payload = self._read_json()
            if tool_call == "reset":
                result = reset_state(scenario_id)
            else:
                result = call_tool(get_state(scenario_id), tool_call, payload)
            self._send(HTTPStatus.OK, {"ok": True, "result": result})
        except Exception as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Edge AIOps HTTP mock tool gateway.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=18090, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MockToolHandler)
    print(f"Edge AIOps mock tool gateway listening on http://{args.host}:{args.port}")
    print("Health: GET /health")
    print("Tool call: POST /tools/{scenario_id}/{tool_call}")
    print("Inspect requests: GET /tools/{scenario_id}/requests")
    print("Inspect trace:    GET /tools/{scenario_id}/trace")
    server.serve_forever()


if __name__ == "__main__":
    main()
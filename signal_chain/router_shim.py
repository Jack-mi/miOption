"""Friday 路由翻译 shim：chat/completions -> 8790 Responses API。

背景（2026-09-23 实测）：本机 Friday 路由 localhost:8790 只说 Responses API，
且其响应载荷对 Codex/langchain 足够、但缺 created_at 等字段，litellm 的严格
解析会炸。本 shim 对外暴露标准 OpenAI chat/completions，对内转发 8790
/v1/responses 并做双向格式翻译，供 DSA(litellm) 等只懂 chat completions 的组件使用。

用法:  python -m signal_chain.router_shim [--port 8799]
v1 范围: 纯文本对话、非流式；带 tools/stream 的请求返回 501（需要时再扩）。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

UPSTREAM = "http://localhost:8790/v1/responses"


def chat_to_responses(payload: dict) -> dict:
    """OpenAI chat.completions 请求 -> Responses API 请求。"""
    instructions: list[str] = []
    input_items: list[dict] = []
    for m in payload.get("messages", []):
        role = m.get("role", "user")
        content = m.get("content") or ""
        if isinstance(content, list):  # 多段内容拼文本
            content = "".join(
                p.get("text", "") if isinstance(p, dict) else str(p) for p in content
            )
        if role == "system":
            instructions.append(content)
        elif role == "assistant":
            input_items.append({
                "role": "assistant",
                "content": [{"type": "output_text", "text": content}],
            })
        else:
            input_items.append({
                "role": "user",
                "content": [{"type": "input_text", "text": content}],
            })
    req: dict = {"model": payload.get("model", "kimi-k3"), "input": input_items}
    if instructions:
        req["instructions"] = "\n\n".join(instructions)
    if payload.get("max_tokens") or payload.get("max_completion_tokens"):
        req["max_output_tokens"] = payload.get("max_tokens") or payload.get("max_completion_tokens")
    return req


def responses_to_chat(resp: dict, model: str) -> dict:
    """Responses API 响应 -> OpenAI chat.completion 响应。"""
    texts: list[str] = []
    for item in resp.get("output", []):
        if item.get("type") != "message":
            continue
        for c in item.get("content", []):
            if c.get("type") == "output_text" and c.get("text"):
                texts.append(c["text"])
    usage = resp.get("usage") or {}
    return {
        "id": resp.get("id") or f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "".join(texts)},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
    }


class ShimHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    upstream: str = UPSTREAM

    def log_message(self, fmt, *args):  # 静默常规访问日志
        pass

    def _send_json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.rstrip("/").endswith("models"):
            self._send_json(200, {"object": "list", "data": [
                {"id": m, "object": "model", "owned_by": "friday-shim"}
                for m in ("kimi-k3", "glm-5.3", "deepseek-v4.1-flash")
            ]})
        else:
            self._send_json(200, {"ok": True, "shim": "friday-chat-shim"})

    def do_POST(self) -> None:
        if not self.path.rstrip("/").endswith("chat/completions"):
            self._send_json(404, {"error": f"unhandled route: {self.path}"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception as exc:
            self._send_json(400, {"error": f"bad request body: {exc}"})
            return

        if payload.get("stream"):
            self._send_json(501, {"error": "stream 暂不支持（v1）；请关闭 stream 后重试"})
            return
        if payload.get("tools") or payload.get("tool_choice"):
            self._send_json(501, {"error": "tools 暂不支持（v1）；该组件需要直连或扩展 shim"})
            return

        req = chat_to_responses(payload)
        t0 = time.monotonic()
        in_chars = sum(len(str(i)) for i in req.get("input", []))
        try:
            with httpx.Client(timeout=httpx.Timeout(600.0, connect=10.0)) as client:
                r = client.post(self.upstream, json=req)
        except Exception as exc:
            print(f"[shim] model={req.get('model')} chars={in_chars} upstream_exc={exc}", file=sys.stderr, flush=True)
            self._send_json(502, {"error": f"upstream unreachable: {exc}"})
            return
        print(f"[shim] model={req.get('model')} chars={in_chars} upstream={r.status_code} "
              f"{time.monotonic()-t0:.1f}s", file=sys.stderr, flush=True)
        if r.status_code != 200:
            self._send_json(r.status_code, {"error": f"upstream {r.status_code}: {r.text[:400]}"})
            return
        try:
            resp = r.json()
        except Exception as exc:
            self._send_json(502, {"error": f"upstream bad json: {exc}"})
            return
        self._send_json(200, responses_to_chat(resp, payload.get("model", "unknown")))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument("--upstream", default=UPSTREAM)
    args = parser.parse_args()
    ShimHandler.upstream = args.upstream
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ShimHandler)
    print(f"friday chat shim listening on 127.0.0.1:{args.port} -> {args.upstream}")
    server.serve_forever()


if __name__ == "__main__":
    main()

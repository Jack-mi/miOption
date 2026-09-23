#!/usr/bin/env python3
"""Serve vault-map H5 + seller-desk API on 127.0.0.1. Does not place orders."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mioption_runtime.ingress.h5 import DEFAULT_STATIC, H5Server  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Local vault-map + seller desk (no orders).")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--static", default=str(DEFAULT_STATIC))
    p.add_argument("--mode", choices=("mock", "live"), default="mock")
    p.add_argument("--chat", action="store_true", help="Start the local OpenCode research chat")
    p.add_argument("--chat-port", type=int, default=4097)
    p.add_argument("--model", default="opencode-go/deepseek-v4-flash")
    p.add_argument("--data-dir", type=Path)
    args = p.parse_args()
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        p.error("this unauthenticated research server is loopback-only")
    if "/" not in args.model:
        p.error("--model must be provider/model")
    state = (args.data_dir or ROOT / "data" / ("mock" if args.mode == "mock" else "live")).resolve()
    state.mkdir(parents=True, exist_ok=True)
    environment = {
        "PYTHONPATH": str(ROOT),
        "MIOPTION_VAULT": str(ROOT.parent / "knowledge"),
        "MIOPTION_FUTU_MOCK": "1" if args.mode == "mock" else "0",
        "MIOPTION_RESEARCH_ONLY": "1",
        "MIOPTION_QUOTES_DB": str(state / "quotes.sqlite"),
        "MIOPTION_SELLER_DIR": str(state / "seller"),
        "MIOPTION_CHAT_MODEL": args.model,
        "MIOPTION_CHAT_URL": f"http://127.0.0.1:{args.chat_port}",
    }
    os.environ.update(environment)
    try:
        server = H5Server(args.host, args.port, static_root=Path(args.static))
    except OSError as exc:
        p.exit(1, f"Cannot bind {args.host}:{args.port}: {exc}. Choose --port; no existing service was stopped.\n")
    child = None
    chat_log = None
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(f"mioption H5 http://{args.host}:{server.port}/chain.html", flush=True)
    print(f"seller desk http://{args.host}:{server.port}/desk.html", flush=True)
    print(f"chat http://{args.host}:{server.port}/chat.html", flush=True)
    print("Chain pull / desk scan only. This server never places orders.", flush=True)
    print(f"mode={args.mode}; data={state}", flush=True)
    try:
        if args.chat:
            executable = shutil.which("opencode")
            if not executable:
                raise RuntimeError("opencode is not installed; start without --chat or install OpenCode")
            import socket

            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", args.chat_port)) == 0:
                    raise RuntimeError(f"Chat port {args.chat_port} is occupied; choose --chat-port")
            config = {
                "mcp": {"mioption": {
                    "type": "local", "command": [sys.executable, "-m", "mioption_runtime.agent.stdio_mcp"],
                    "environment": environment, "enabled": True,
                }},
            }
            child_env = {
                **os.environ,
                "OPENCODE_CONFIG_CONTENT": json.dumps(config),
                "OPENCODE_DISABLE_EXTERNAL_SKILLS": "true",
                "OPENCODE_DISABLE_CLAUDE_CODE": "true",
            }
            chat_log = (state / "opencode.log").open("a", encoding="utf-8")
            child = subprocess.Popen(
                [executable, "serve", "--pure", "--hostname", "127.0.0.1", "--port", str(args.chat_port),
                 "--cors", f"http://{args.host}:{server.port}"],
                cwd=ROOT.parent, env=child_env, stdout=chat_log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            deadline = time.monotonic() + 30
            while True:
                if child.poll() is not None:
                    raise RuntimeError(f"Chat exited; see {state / 'opencode.log'}")
                try:
                    with urlopen(f"{environment['MIOPTION_CHAT_URL']}/global/health", timeout=1) as response:
                        if json.load(response).get("healthy"):
                            break
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"Chat did not become ready; see {state / 'opencode.log'}")
                time.sleep(0.2)
        server.start_background()
        print("READY", flush=True)
        while True:
            if child is not None and child.poll() is not None:
                raise RuntimeError("Chat process exited; restart the workbench")
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        if server._thread is not None:
            server.stop()
        else:
            server.httpd.server_close()
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        if chat_log is not None:
            chat_log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

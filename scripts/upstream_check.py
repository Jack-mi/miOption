#!/usr/bin/env python3
"""上游版本检查与升级演练（方案 v5）。

默认（只读）：对比 vendor.lock.json 钉版与上游最新 commit，输出差异，不改动任何东西。
--probe     ：探测本机 8790 /v1/responses 可用性。
--upgrade <name>：演练升级（拉新版 -> 重 apply patch -> 契约测试），全绿才提示更新 lock。

绝不自动升级；lock 更新永远是人确认后的手动动作。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCK = REPO_ROOT / "vendor.lock.json"


def _git(args: list[str], cwd: Path, check: bool = True) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, check=check).stdout.strip()


def load_lock() -> dict:
    return json.loads(LOCK.read_text(encoding="utf-8"))


def probe_router(base_url: str = "http://localhost:8790") -> bool:
    payload = json.dumps({
        "model": "kimi-k3",
        "input": "回复两个字：正常",
        "max_output_tokens": 16,
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/v1/responses", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        ok = data.get("object") == "response" or "output" in data
        print(f"probe 8790 /v1/responses: {'OK' if ok else 'UNEXPECTED: ' + str(data)[:200]}")
        return ok
    except Exception as exc:
        print(f"probe 8790 /v1/responses FAILED: {exc}")
        return False


def check_versions() -> int:
    lock = load_lock()
    stale = 0
    for v in lock["vendors"]:
        path = REPO_ROOT / v["path"]
        if not path.exists():
            print(f"[{v['name']}] vendor 目录缺失: {path}")
            stale += 1
            continue
        try:
            _git(["fetch", "origin", "--depth", "64", "main"], path)
            latest = _git(["rev-parse", "origin/main"], path)
        except subprocess.CalledProcessError as exc:
            print(f"[{v['name']}] fetch 失败: {exc.stderr.strip()[:200]}")
            continue
        pinned = v["commit"]
        if latest == pinned:
            print(f"[{v['name']}] 已是最新 ({pinned[:8]})")
        else:
            count = _git(["rev-list", "--count", f"{pinned}..origin/main"], path)
            log = _git(["log", "--oneline", f"{pinned}..origin/main", "-5"], path)
            print(f"[{v['name']}] 落后 {count} 个 commit:\n{log}")
            stale += 1
    return 0 if stale == 0 else 1


def _rollback(path: Path, pinned: str, patches: list[str]) -> None:
    _git(["checkout", "--", "."], path, check=False)
    _git(["checkout", pinned], path)
    for patch in patches:
        _git(["apply", str(REPO_ROOT / patch)], path, check=False)


def upgrade(name: str) -> int:
    """演练：fetch 新版 -> 检出 -> 重 apply patch -> 契约测试。lock 不自动改。"""
    lock = load_lock()
    vendor = next((v for v in lock["vendors"] if v["name"] == name), None)
    if vendor is None:
        print(f"未知 vendor: {name}")
        return 2
    path = REPO_ROOT / vendor["path"]
    pinned = vendor["commit"]
    patches = vendor.get("patches", [])

    print(f"[{name}] fetch 最新...")
    _git(["fetch", "origin", "--depth", "64", "main"], path)
    latest = _git(["rev-parse", "origin/main"], path)
    if latest == pinned:
        print(f"[{name}] 已是最新，无需演练")
        return 0

    print(f"[{name}] 检出 {latest[:8]}（演练，失败回滚 {pinned[:8]}）...")
    _git(["checkout", "--", "."], path, check=False)
    _git(["checkout", latest], path)

    for patch in patches:
        patch_path = REPO_ROOT / patch
        rc = subprocess.run(["git", "apply", "--check", str(patch_path)],
                            cwd=path, capture_output=True, text=True)
        if rc.returncode != 0:
            print(f"[{name}] 红灯：patch 无法应用于新版本:\n{rc.stderr[:400]}")
            _rollback(path, pinned, patches)
            return 1
        _git(["apply", str(patch_path)], path)
        print(f"[{name}] patch 重应用成功: {patch}")

    print(f"[{name}] 跑契约测试...")
    rc = subprocess.run(
        [str(REPO_ROOT / ".venv-sc/bin/python"), "-m", "pytest",
         "signal_chain/tests/contracts", "-x", "-q"],
        cwd=REPO_ROOT,
    )
    if rc.returncode != 0:
        print(f"[{name}] 红灯：契约测试失败。回滚。")
        _rollback(path, pinned, patches)
        return 1

    print(f"[{name}] 演练全绿。请人工确认后更新 vendor.lock.json: "
          f"{pinned[:8]} -> {latest[:8]}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", help="探测 8790 /v1/responses")
    parser.add_argument("--upgrade", metavar="NAME", help="演练升级指定 vendor")
    args = parser.parse_args()

    if args.probe:
        sys.exit(0 if probe_router() else 1)
    if args.upgrade:
        sys.exit(upgrade(args.upgrade))
    sys.exit(check_versions())


if __name__ == "__main__":
    main()

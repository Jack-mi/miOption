from __future__ import annotations


def get_json(url: str, headers: dict | None = None, timeout: float = 20):
    import httpx

    response = httpx.get(url, headers=headers or {}, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    text = response.text.lstrip()
    if text.startswith(("{", "[")):
        return response.json()
    raise ValueError(f"非 JSON: {text[:120]}")


def get_text(url: str, headers: dict | None = None, timeout: float = 20) -> str:
    import httpx

    response = httpx.get(url, headers=headers or {}, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return response.text

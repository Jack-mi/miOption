# miOption FastMCP server

One stdio entry for every host:

```bash
# from repo, using the runtime venv (has futu-api + fastmcp==4.0.3)
runtime/.venv/bin/python -m mioption_runtime.agent.stdio_mcp
```

Required environment (Cursor isolates MCP from your shell):

| Variable | Default in `.cursor/mcp.json` |
|---|---|
| `PYTHONPATH` | `<repo>/runtime` |
| `MIOPTION_FUTU_MOCK` | `0` (this workspace; examples under `embed/hosts/` stay `1`) |
| `MIOPTION_VAULT` | `<repo>/knowledge` |

Do not use `uv run --with fastmcp` as the launch command; that environment will not include `futu-api`.

Do not serve HTTP/SSE by default. OpenD is localhost TCP.

Cursor is wired in [`.cursor/mcp.json`](../../.cursor/mcp.json). Other hosts: [`../hosts/`](../hosts/).

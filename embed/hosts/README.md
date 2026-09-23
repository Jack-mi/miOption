# Host adapters (thin)

These files only point at the shared FastMCP command. They do not copy Futu or bot code.

Canonical skill: [`../skills/mioption/SKILL.md`](../skills/mioption/SKILL.md)

| Host | File | Notes |
|---|---|---|
| Cursor | [`cursor/mcp.json.example`](cursor/mcp.json.example) | Already applied as repo [`.cursor/mcp.json`](../../.cursor/mcp.json) |
| Claude Code | [`claude-code/`](claude-code/) | plugin.json + `.mcp.json`; replace `<repo>` |
| Codex | [`codex/config.toml.example`](codex/config.toml.example) | Optional overlay, not the default harness |
| OpenCode | [`opencode/opencode.mcp.snippet.json`](opencode/opencode.mcp.snippet.json) | Applied as repo [`opencode.json`](../../opencode.json). OpenCode 1.18 uses `mcp.<name>` (not V2 `mcp.servers`). |

The vault-map H5 chat panel talks to `opencode serve` (default `127.0.0.1:4096`).

## Optional read-only technical-analysis MCP

[`codex/tradingview-mcp.toml.example`](codex/tradingview-mcp.toml.example) adds the independently maintained `tradingview-mcp` service. It uses a dedicated Python 3.13 environment pinned to `tradingview-mcp-server==0.8.1`, because that release declares Python `<3.14`. It provides external market data, technical indicators, screeners, and backtests only; it is intentionally separate from the `mioption` FastMCP server and never receives Futu/OpenD or order tools.

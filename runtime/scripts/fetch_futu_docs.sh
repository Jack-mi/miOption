#!/usr/bin/env bash
# Download Futu OpenAPI Markdown for agent context (optional; may be gitignored).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="${ROOT}/docs/futu-api"
mkdir -p "${DEST}"
echo "Futu docs are downloaded from the OpenAPI site UI (Download → Markdown)."
echo "Place extracted .md files under: ${DEST}"
echo "Reference: https://openapi.futunn.com/futu-api-doc/intro/ai.html"
echo "Optional skills zip: https://openapi.futunn.com/skills/opend-skills.zip"
# Keep a stub so the path exists in-repo without a multi-MB dump.
cat > "${DEST}/README.md" <<'EOF'
# Futu OpenAPI docs (local cache)

Download Markdown from the official site (page menu → Download → Markdown) and
unpack here for agent retrieval.

- Portal: https://openapi.futunn.com/futu-api-doc/
- AI onboarding: https://openapi.futunn.com/futu-api-doc/intro/ai.html
- Skills zip: https://openapi.futunn.com/skills/opend-skills.zip

Do not commit large generated dumps if they bloat the repo; re-run the site
download or keep them locally gitignored.
EOF
echo "Wrote ${DEST}/README.md"

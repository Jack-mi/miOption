# Futu OpenAPI docs (local cache)

Download Markdown from the official site (page menu → Download → Markdown) and
unpack here for agent retrieval.

- Portal: https://openapi.futunn.com/futu-api-doc/
- AI onboarding: https://openapi.futunn.com/futu-api-doc/intro/ai.html
- Skills zip: https://openapi.futunn.com/skills/opend-skills.zip

已落地（gitignored，不进版本库）：

- `Futu-API-Doc-zh-Python.md` —— 全量官方文档（Python/中文，约 1 MB，148 个接口，含每个接口的限频与权限说明）。
  刷新：`curl -sL -o docs/futu-api/Futu-API-Doc-zh-Python.md https://openapi.futunn.com/mds/Futu-API-Doc-zh-Python.md`

Do not commit large generated dumps if they bloat the repo; re-run the site
download or keep them locally gitignored.

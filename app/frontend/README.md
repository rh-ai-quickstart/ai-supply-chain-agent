# AI Supply Chain Agent — Frontend

React 19 + Vite SPA for impact simulation, streaming chat, and knowledge-base management.

## Scripts

```bash
pnpm install
pnpm dev          # Vite on :5173, proxies /api → http://127.0.0.1:5001
pnpm test         # Vitest (jsdom)
pnpm run lint     # ESLint
pnpm run build    # Production bundle → dist/
```

Override the API proxy target with `VITE_DEV_API_PROXY_TARGET` (see `vite.config.js`).

## Views

Hash routes (no React Router):

| Hash | View |
|------|------|
| `#/simulation?scenario=…` | Impact query + map + results, plus chat dock |
| `#/knowledge-bases` | Create/list Llama Stack knowledge bases |

Chat auto-selects a vector store for the active scenario by keyword match on store names.

## Production image

`Containerfile` builds with pnpm and serves `dist/` via nginx-unprivileged on port 8080. Nginx proxies `/api/` to `BACKEND_UPSTREAM` (set by Helm).

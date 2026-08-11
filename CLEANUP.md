# Cleanup Candidates

Audit findings — unused / dead / dormant code across the repo. Nothing here is
blocking; items are grouped by confidence so you can decide how aggressive to be.

## Backend — genuinely dead (safe to delete)

| Location | Item | Why dead |
|---|---|---|
| `app/backend/api/clients/chat_completion_client.py:128-130` | `LlamaStackChatClient._client` property | Never accessed; callers use the facade's `_client` |
| `app/backend/api/clients/chat_completion_client.py:185` | `_completion_to_json` alias | Only the facade version is ever called |
| `app/backend/api/clients/chat_completion_client.py:223` | `_completion_kwargs` alias | Only the facade version is ever called |
| `app/backend/api/clients/llama_stack_client.py:111-112` | facade `_build_messages` | No callers anywhere (prod or tests) |
| `app/backend/api/clients/llama_stack_client.py:34` | `_StreamAccumulator` re-export (`# noqa: F401`) | No consumers import it from this module |
| `app/backend/api/clients/vector_store_client.py:59-61` | `as_retriever` method | Never called |
| `app/backend/api/repositories/json_file_store.py:24` | `path` property | Never read |
| `app/backend/api/services/chat_service.py:9,16` | `GUARDRAIL_RESPONSE` import + `_GUARDRAIL_RESPONSE` alias | Only tests consume the alias |
| `app/backend/api/services/chat_service.py:26,243` | `_PreparedChatTurn.history` field | Assigned but never read |

## Backend — test-only (production never calls; remove only if tests change)

| Location | Item | Production path |
|---|---|---|
| `app/backend/api/clients/llama_stack_client.py:122-126` | facade `ask` / `ask_stream` | Prod uses `ask_with_tools` / `ask_stream_with_tools` |
| `app/backend/api/services/agent_service.py:137` | `tools` property | Prod uses `openai_tools()` |
| `app/backend/api/services/general_simulation_service.py:13-14` | `check_health` | Readiness probes the client directly |
| `app/backend/api/repositories/knowledge_base_repository.py:38-39` | `append` | Prod uses `append_upload` |

## Backend — latent / dormant

| Location | Item | Note |
|---|---|---|
| `app/backend/api/errors.py` | `AppError`, `ValidationError`, `NotFoundError`, `UpstreamServiceError` | `register_error_handlers` is wired in `app_factory.py:38`, but no production code raises these — only tests. Either start raising them or delete the hierarchy. |
| `app/backend/ingestion/clients/vector_store_client.py`, `app/backend/ingestion/services/ingestion_service.py`, `app/backend/ingestion/loaders/document_loader.py` | Legacy "langchain" ingestion strategy | Only reachable via `INGEST_STRATEGY=langchain`. Default is `llamastack` everywhere (`ingestion/config.py:17`, `helm/values.yaml:184`, `Makefile:451`). Largest removable chunk if the strategy is retired. |

## Backend — unused test imports

| Location | Unused import |
|---|---|
| `app/backend/tests/api/test_agent_service.py:3` | `ToolResult` |
| `app/backend/tests/api/test_container.py:3` | `MagicMock` |
| `app/backend/tests/api/test_general_simulation_service.py:7` | `pytest` |

## Frontend — no orphaned files

| Location | Item | Note |
|---|---|---|
| `app/frontend/src/components/ImpactQueryPanel.jsx:2` | Unused `DEFAULT_IMPACT_QUESTION` import | Only ESLint warning in `src/`; `labelForScenario` is the one actually used |
| `app/frontend/src/services/presetScenarioIds.js:7,13,26,35` | Exports `SCENARIO_LABELS`, `SCENARIO_QUESTIONS`, `SCENARIO_BBOXES`, `SCENARIO_VECTOR_STORE_KEYWORDS` | Never imported outside the module; only used internally. Drop the `export` keyword, not the constants |
| `app/frontend/src/services/presetScenarioIds.js:76,81` | Exports `vectorStoreKeywordsForScenario`, `findVectorStoreId` | Never imported outside the module; used internally by `findVectorStoreIdForScenario`. Drop `export` |
| `app/frontend/src/utils/errorMessage.js:9` | `isAbortError` export | Consumed only by its own test file (used internally) |
| `app/frontend/src/services/presetScenarioIds.js:53` | `humanizeScenarioId` export | Consumed only by its own test file (used internally) |

## Helm — minor gaps

| Location | Item | Note |
|---|---|---|
| `helm/templates/frontend-deployment.yaml:2` | `frontend.apiProxyUpstream` | Referenced but not defined or documented in `values.yaml`. It's a tested override that defaults gracefully, but it's undocumented — add it to `values.yaml` or remove it. |
| `helm/secrets.yaml` | Live-looking API keys on disk | File is gitignored/untracked (no exposure), but contains what appear to be real OpenAI + MaaS tokens. Rotate and prefer `secrets.example.yaml` placeholders. |

## CI — redundancy (not dead)

| Location | Item | Note |
|---|---|---|
| `.github/workflows/helm-tests.yml` vs `.github/workflows/kind-helm-smoke.yml` | Duplicate `make helm-test` | `kind-helm-smoke.yml:3` claims it "replaces separate helm-tests workflow," but both still exist and run `make helm-test` on overlapping `helm/**` triggers. Consolidate to one workflow. |

## Verified used — do NOT remove

Everything else was confirmed as actively referenced:

- Backend: all `api/clients/*`, `api/services/*`, `api/repositories/*`, all settings fields (incl. `git_commit`/`build_time` served by `/api/v1/version`), `errors.py`/`register_error_handlers`, `run_backend_tests.py`, `ingestion/knowledge_base/*.txt`
- Frontend: all 11 components, 7 hooks, 7 services, 6 utils, `version.js`, `index.css`, `public/vite.svg`, `nginx/default.conf.template`, `Containerfile`, all test files
- Helm: all 9 templates (all unit-tested), all `values.yaml` keys (umbrella templates + subcharts), `values-kind.yaml`, `secrets.example.yaml`, `Chart.lock` + `charts/*.tgz`
- Scripts / CI / docs / infra: `scripts/ci/*`, `scripts/seed-*.sh`, all 4 workflows, `docs/WHAT_TO_EXPECT.md`, root docs, `infra/prereqs/ocp-gpu-setup/`, `tests/e2e_ui/`

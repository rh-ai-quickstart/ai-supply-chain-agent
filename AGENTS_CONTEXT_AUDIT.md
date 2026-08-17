# Context Management Audit - Complete

## Requirement Status

### ✅ Requirement 1: Selected Scenario KB → Agent Context
- **Flow**: `activeScenarioId` → `findVectorStoreIdForScenario()` → frontend sends `vector_store_id` → `ChatService._retrieve_context()` → `RagContextProvider.get_context()` → context appended to system prompt
- **Enhancement (this pass)**: The active scenario is now also named in the LLM context via a dedicated `scenario_context` block (e.g. `Active scenario: opensky-uk-closure-001 (UK Airspace Closure).`), threaded through `_prepare_llm_turn` → `ask_with_tools`/`ask_stream_with_tools` → `build_messages`. So the model sees both the RAG KB context AND an explicit active-scenario header.

### ✅ Requirement 2: Clear Context
- `clearChat()` on the frontend resets messages/input/error/loading/simulation for the active scenario only.
- Backend is stateless: empty `chat_history: []` drops user/AI turns while the system prompt + KB + scenario context remain.
- UI: "Clear conversation" button in the chat bar row AND in the modal header (reachable after a reply auto-opens the modal).

### ✅ Requirement 3: Tools Always Added + Scenario Tool
- 4 tools registered every call: `general_simulation`, `knowledge_base`, `fetch_news`, `news_knowledge_base`.
- KB tool auto-binds `vector_store_id`; simulation tool auto-resolves `scenario_id` via `normalize_scenario_id()`.
- **Enhancement (this pass)**: `SYSTEM_PROMPT` now names **all 4** tools (previously omitted `news_knowledge_base`). A parity test guards against prompt/tool drift.

## Files Changed

| File | Change |
|------|--------|
| `app/frontend/src/hooks/useChatSession.js` | `clearChat()` callback (messages/input/error/loading/simulation) |
| `app/frontend/src/hooks/useChatSession.test.js` | +4 tests (clear behavior, per-scenario isolation, KB persistence, loading/simulation reset) |
| `app/frontend/src/components/ChatBar.jsx` | "Clear conversation" button (bar row + modal header), `onClearChat` prop, `onClick={() => onClearChat()}` guard |
| `app/frontend/src/components/ChatBar.test.jsx` | +5 tests (hidden when empty, calls handler w/ no event, modal-header w/ no event, hidden while loading) |
| `app/frontend/src/App.jsx` | Wired `onClearChat={clearChat}` |
| `app/backend/api/clients/chat_completion_client.py` | `SYSTEM_PROMPT` lists all 4 tools; `build_messages`/`ask`/`ask_stream` accept `scenario_context` |
| `app/backend/api/clients/tool_loop_orchestrator.py` | `ask_with_tools`/`ask_stream_with_tools` thread `scenario_context` |
| `app/backend/api/services/chat_service.py` | `_prepare_llm_turn` computes `scenario_context`; passed to both reply paths |
| `app/backend/api/services/simulation_intent.py` | `scenario_context_block()` helper + label map |
| `app/backend/tests/api/test_chat_service.py` | +10 tests (scenario context sync/stream, empty context, block ordering, prompt/tool parity, cleared-history context) |
| `tests/e2e_ui/test_chat_ui.py` | +1 e2e test: clear conversation removes messages, keeps KB status |

## Test Results (verified)

- **Frontend**: 233 passed
- **Backend**: 169 API + 11 ingestion = 180 passed
- **Lint**: eslint clean, ruff clean (pre-existing `test_errors.py` issues untouched), mypy clean
- **E2E**: 2 chat tests pass against local backend on 5001 (`SUPPLY_CHAIN_UI_ENDPOINT=http://localhost:5173 BACKEND_HEALTH_URL=http://127.0.0.1:5001/healthz`)

## Bug Fix (re-applied this session)

**Bug**: "Clear conversation" did nothing. `onClick={onClearChat}` passed the React click event into `clearChat(scenarioKeyOverride)`, and `clearChat` used `let key = scenarioKeyOverride || chatKey;` — the truthy event object became the state key, so the real scenario key was never cleared.

**Fix**: Both buttons now use `onClick={() => onClearChat()}`; regression tests assert `toHaveBeenCalledWith()` (no event arg) for the bar-row button and the modal-header button.

**E2E note**: run chat E2E against the local dev backend (port 5001), not the cluster port-forward — the 15001 forward is flaky and produces empty AI bubbles.

## Commands

```bash
# Frontend
cd app/frontend && npm test -- --no-coverage
npx eslint src/components/ChatBar.jsx src/hooks/useChatSession.js src/App.jsx

# Backend
cd app/backend && ./venv/bin/python run_backend_tests.py
./venv/bin/ruff check api tests
./venv/bin/mypy --config-file mypy.ini api

# E2E (needs running UI/backend)
cd <repo root> && python -m pytest tests/e2e_ui/ -v --tb=short --browser chromium
```

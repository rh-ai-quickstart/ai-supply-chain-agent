# AI Supply Chain Agent — Detailed Description

## Detailed description

### Who is this for?

This quickstart guide is designed for:

- **Supply chain operators and managers** who need real-time visibility into global logistics risk
- **DevOps and platform engineers** deploying AI-powered operational dashboards on OpenShift
- **Solution architects** evaluating RAG-based AI systems for industrial or logistics use cases
- **Organizations** looking to integrate generative AI into supply chain monitoring and decision support
- **AI practitioners** interested in hands-on experience running Llama Stack, PGVector, and vLLM on OpenShift AI

---

### The business case for AI-powered supply chain intelligence

Global supply chains are increasingly vulnerable to disruptions — from natural disasters and geopolitical events to labor disputes and infrastructure failures. Traditional dashboards can surface alerts, but they cannot reason about them. Operators are left interpreting raw metrics without the context needed to understand root causes, project downstream impacts, or decide on corrective actions quickly.

Generative AI changes this by bringing a reasoning layer directly into the operations center. The key value propositions are:

**For supply chain operators**

- **Faster situational awareness.** Rather than reading through reports or calling subject matter experts, operators can ask natural-language questions grounded in a curated knowledge base of past disruptions and risk analyses.
- **AI-assisted disruption response.** When a scenario such as a port strike or geopolitical event is triggered, the AI assistant provides context-aware guidance drawn from historical incident analyses.
- **Continuous monitoring.** Live KPIs, logistics maps, and alert feeds refresh automatically so operators maintain an accurate picture of global operations at all times.

**For operations leadership**

- **Disruption simulation.** Teams can model the impact of hypothetical events — port strikes, Suez Canal blockages, regional weather — before they occur, enabling proactive contingency planning.
- **Infrastructure comparison.** A built-in performance toggle demonstrates the throughput and latency improvements of distributed LLM inference (vLLM + LLM-D) versus standard monolithic serving, supporting infrastructure investment decisions.
- **Extensible knowledge base.** Custom risk analyses, incident reports, and policy documents can be uploaded at runtime and immediately queried through the AI chat interface.

---

### What this quickstart provides

This quickstart provides a complete, deployable reference architecture for an AI-powered supply chain intelligence platform on Red Hat OpenShift. It includes:

- A **standalone React SPA** for operators: impact simulation (scenario query, Leaflet map, solver results), streaming RAG chat, and knowledge-base management
- A **Flask backend API** proxying general-simulation impact queries, AI chat, and knowledge base management
- A **knowledge base ingestion pipeline** that loads pre-built supply chain risk analyses into Llama Stack vector stores or PGVector for RAG retrieval
- A **Helm umbrella chart** that deploys the full stack — frontend, backend, ingest job, Llama Stack, LLM service, and PGVector — with a single command

---

### What you'll build

Time to complete: 30–90 minutes (depending on deployment mode and hardware)

By the end of this quickstart, you will have:

- A fully functional AI supply chain impact workspace deployed on OpenShift
- A RAG-powered AI chatbot grounded in supply chain risk knowledge (Suez Canal blockage, Port Strike LA, UK NATS GPS airspace closure, and more)
- Impact simulation against general-simulation scenarios: affected entities, value-at-risk, recommended diversions, and an interactive map
- A knowledge base management interface for uploading and querying custom risk documents at runtime
- Streaming chat completions with per-scenario conversation history and auto-matched vector stores

---

### Key technologies you'll learn

Throughout this quickstart, you'll gain hands-on experience with modern AI and cloud-native technologies:

**AI & LLM Technologies:**
- **[Llama Stack](https://github.com/meta-llama/llama-stack)** — OpenAI-compatible API for chat completions, embeddings, and vector store management
- **[vLLM](https://docs.vllm.ai/)** — High-throughput LLM serving engine; the default inference backend for `meta-llama/Llama-3.2-3B-Instruct`
- **[LLM-D](https://github.com/llm-d/llm-d)** — Distributed LLM inference for disaggregated prefill/decode; demonstrated via the performance comparison toggle
- **[RAG (Retrieval-Augmented Generation)](https://www.redhat.com/en/topics/ai/what-is-retrieval-augmented-generation)** — Dual-path RAG with Llama Stack vector stores (default) and LangChain + PGVector (alternative strategy)
- **[LangChain](https://python.langchain.com/)** — Embeddings pipeline and PGVector similarity search integration
- **[Llama 3.2](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct)** — Default tool-capable instruct model for supply chain query answering

**Frontend & Visualization:**
- **[React 19](https://react.dev/) + [Vite 7](https://vitejs.dev/)** — Standalone operator SPA
- **[Leaflet 1.9](https://leafletjs.com/) + react-leaflet 5** — Interactive impact map with entity highlights and diversion routes
- **[react-markdown](https://github.com/remarkjs/react-markdown)** — Streaming chat and impact-answer rendering

**Cloud-Native Infrastructure:**
- **[OpenShift 4.21+](https://www.redhat.com/en/technologies/cloud-computing/openshift) / [OpenShift AI 3.4+](https://www.redhat.com/en/technologies/cloud-computing/openshift/openshift-ai)** — Container orchestration and AI/ML platform
- **[Helm 3](https://helm.sh/)** — Umbrella chart with AI architecture subcharts for one-command deployment
- **[PGVector](https://github.com/pgvector/pgvector)** — PostgreSQL extension for vector similarity search
- **[OpenSky Network API](https://openskynetwork.github.io/opensky-api/)** — Live aircraft position data for air-freight logistics map

---

### Architecture overview

The platform is built as a React frontend and Flask backend API:

```
┌──────────────────────────────────────────────────────────────┐
│                        User Interface                         │
│                                                               │
│                   Standalone React SPA                        │
│                      (nginx :8080)                            │
└─────────────────────────────┬────────────────────────────────┘
                              │    /api/* proxy
┌─────────────────────────────▼────────────────────────────────┐
│                     Flask Backend API (:5001)                  │
│                                                               │
│  GeneralSimulation   ChatService    KnowledgeBases           │
│  (impact query/map)  (RAG + LLM)    (ingest + catalog)       │
└──────────┬──────────────────┬────────────────────────────────┘
           │                  │
┌──────────▼──────┐  ┌────────▼─────────────────────────────── ┐
│  Llama Stack     │  │  PGVector (PostgreSQL)                   │
│  (:8321)         │  │  LangChain RAG fallback                  │
│  LLM Service     │  │                                          │
│  (vLLM / LLM-D)  │  │                                          │
└──────────────────┘  └─────────────────────────────────────────┘
```

**Key request flows:**

1. **Impact simulation:** The operator picks a seeded scenario and runs a natural-language impact query (`POST /api/v1/general-simulation/query`). The backend forwards to general-simulation; the UI shows impact score, value at risk, affected entities, recommended diversions, and highlights entities on a GeoJSON map (`GET .../entities/geojson`).

2. **AI chat (RAG):** The operator types a question in the chat dock. `POST /api/v1/chat` runs guardrails, then RAG against an auto-matched vector store for the active scenario. With `stream: true` (UI default), the backend relays token chunks over SSE so the reply renders incrementally as markdown.

3. **Knowledge base ingestion:** A post-install Kubernetes Job loads bundled risk analyses (UK NATS GPS airspace closure, Port Strike LA/LGB, Suez Canal blockage) into Llama Stack vector stores — one store per document so scenarios can select the matching knowledge base by name keywords. Operators can also upload custom `.txt`/`.pdf` documents at runtime via the knowledge base page.

**Bundled knowledge base documents:**

| Document | Topic | Simulation scenario |
|----------|-------|---------------------|
| `air_risk_uk_nats_gps_closure.txt` | UK NATS GPS/navigation failure: diversions, oceanic contingency tracks, air-freight impact | `opensky-uk-closure-001` |
| `land_risk_port_strike_la.txt` | LA/LGB port strike: vessel holds, inland DC shortfalls, Oakland/Prince Rupert reroutes | `supply-chain-port-strike-la` |
| `suez_blockage_analysis.txt` | Suez corridor blockage: Cape diversion (~14 days), Rotterdam backlog, high-value cargo VaR | `supply-chain-suez-blockage` |

**Impact scenarios (UI):**

| Scenario ID | Label | Focus |
|-------------|-------|-------|
| `opensky-uk-closure-001` | UK Airspace Closure | Aircraft diversions / air cargo VaR |
| `supply-chain-port-strike-la` | Port Strike LA | Vessel / inland facility impact |
| `supply-chain-suez-blockage` | Suez Blockage | Delayed vessels and European port backlog |

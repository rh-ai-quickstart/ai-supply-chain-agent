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

- A **standalone React dashboard** for operators with KPIs, live charts, a logistics map, and a RAG-powered AI chatbot
- An **OpenShift Console plugin** that embeds the same dashboard inside a dedicated Supply Chain perspective in the OpenShift web console
- A **Flask backend API** managing dashboard state, disruption simulations, AI chat, and knowledge base management
- A **knowledge base ingestion pipeline** that loads pre-built supply chain risk analyses into Llama Stack vector stores or PGVector for RAG retrieval
- A **Helm umbrella chart** that deploys the full stack — frontend, backend, ingest job, Llama Stack, LLM service, and PGVector — with a single command

---

### What you'll build

Time to complete: 30–90 minutes (depending on deployment mode and hardware)

By the end of this quickstart, you will have:

- A fully functional AI supply chain dashboard deployed on OpenShift
- A RAG-powered AI chatbot grounded in supply chain risk knowledge (Suez Canal blockage, US trucking shortage, Iceland ash cloud, and more)
- Live and simulated dashboard data including KPIs, demand/revenue charts, alerts, and a Leaflet logistics map with air-freight tracking via OpenSky
- Working disruption simulation scenarios (port strike, geopolitical event) that dynamically update KPIs and inject critical alerts
- A knowledge base management interface for uploading and querying custom risk documents at runtime
- Experience with the vLLM & LLM-D performance toggle that surfaces distributed inference metrics
- (Optional) An OpenShift Console perspective integration via a dynamic console plugin

---

### Key technologies you'll learn

Throughout this quickstart, you'll gain hands-on experience with modern AI and cloud-native technologies:

**AI & LLM Technologies:**
- **[Llama Stack](https://github.com/meta-llama/llama-stack)** — OpenAI-compatible API for chat completions, embeddings, and vector store management
- **[vLLM](https://docs.vllm.ai/)** — High-throughput LLM serving engine; the default inference backend for `meta-llama/Llama-3.2-1B-Instruct`
- **[LLM-D](https://github.com/llm-d/llm-d)** — Distributed LLM inference for disaggregated prefill/decode; demonstrated via the performance comparison toggle
- **[RAG (Retrieval-Augmented Generation)](https://www.redhat.com/en/topics/ai/what-is-retrieval-augmented-generation)** — Dual-path RAG with Llama Stack vector stores (default) and LangChain + PGVector (alternative strategy)
- **[LangChain](https://python.langchain.com/)** — Embeddings pipeline and PGVector similarity search integration
- **[Llama 3.2](https://llama.meta.com/)** — 1B-parameter instruction-tuned model for supply chain query answering

**Frontend & Visualization:**
- **[React 19](https://react.dev/) + [Vite 7](https://vitejs.dev/)** — Standalone operator dashboard SPA
- **[Chart.js 4](https://www.chartjs.org/) + react-chartjs-2** — Demand forecasting and revenue trend charts
- **[Leaflet 1.9](https://leafletjs.com/) + react-leaflet 5** — Interactive logistics map with global, regional, and air-freight views
- **[PatternFly 6](https://www.patternfly.org/)** — OpenShift-native UI components for the console plugin
- **[@openshift-console/dynamic-plugin-sdk](https://github.com/openshift/console/tree/master/frontend/packages/dynamic-plugin-sdk)** — Embeds the dashboard as a first-class OpenShift Console perspective

**Cloud-Native Infrastructure:**
- **[OpenShift 4.21+](https://www.redhat.com/en/technologies/cloud-computing/openshift) / [OpenShift AI 3.4+](https://www.redhat.com/en/technologies/cloud-computing/openshift/openshift-ai)** — Container orchestration and AI/ML platform
- **[Helm 3](https://helm.sh/)** — Umbrella chart with AI architecture subcharts for one-command deployment
- **[PGVector](https://github.com/pgvector/pgvector)** — PostgreSQL extension for vector similarity search
- **[OpenSky Network API](https://openskynetwork.github.io/opensky-api/)** — Live aircraft position data for air-freight logistics map

---

### Architecture overview

The platform is built as three integrated layers sharing a single Flask backend API:

```
┌──────────────────────────────────────────────────────────────┐
│                        User Interfaces                        │
│                                                               │
│   Standalone React SPA          OpenShift Console Plugin      │
│   (nginx :8080)                 (PatternFly :9001)            │
└─────────────────────┬───────────────────────┬────────────────┘
                      │    /api/* proxy        │
┌─────────────────────▼───────────────────────▼────────────────┐
│                     Flask Backend API (:5001)                  │
│                                                               │
│  DashboardService   ChatService    RouteService               │
│  (KPIs, map, alerts) (RAG + LLM)  (routing optimization)     │
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

1. **Dashboard refresh (every 15 seconds):** The frontend polls `GET /api/v1/state`. The `DashboardService` assembles KPIs, chart data, alert feeds, and map layers — enriching with live OpenSky aircraft positions when available — and returns a single state JSON.

2. **Disruption simulation:** The operator selects a scenario preset in the Simulation Panel and clicks Simulate. A `POST /api/v1/simulate` request mutates KPIs and injects critical alerts for the selected scenario (e.g. Port Strike LA, Suez blockage). The frontend replaces dashboard state immediately without waiting for the next poll cycle.

3. **AI chat (RAG):** The operator types a question in the chat panel. `POST /api/v1/chat` runs the request through guardrails (off-topic rejection), an optional deterministic route-optimization shortcut, then a full RAG pipeline: vector similarity search against the knowledge base, followed by an LLM completion via Llama Stack. Responses are streamed back as markdown.

4. **Knowledge base ingestion:** A post-install Kubernetes Job loads bundled risk analyses (Suez Canal, US trucking shortage, Iceland ash cloud) into Llama Stack vector stores. Operators can also upload custom `.txt`/`.pdf` documents at runtime via the knowledge base management panel.

**Bundled knowledge base documents:**

| Document | Topic |
|----------|-------|
| `suez_blockage_analysis_2021.txt` | Ever Given incident: root causes, delays, global trade impact |
| `land_risk_us_trucking_shortage_2023.txt` | Driver shortage, freight cost surge, port backlog metrics |
| `air_risk_iceland_ash_cloud_2010.txt` | Eyjafjallajökull eruption: airspace closure, air-freight disruption |

**Simulation scenarios:**

| Scenario | Dashboard effect |
|----------|-----------------|
| Port Strike (LA/LGB) | Lost-sales KPI → $4.2M; critical port-strike alert injected |
| Geopolitical Event | Turnover KPI drops; Suez blockage 14-day delay alert injected |
| World Event (map) | Ephemeral map-layer alerts (cyclone, labor dispute, airspace closure) with 120-second TTL |

**vLLM & LLM-D performance toggle:**

When enabled, the dashboard adds a Performance Metrics panel surfacing synthetic latency, cache-hit rate, and tokens-per-second statistics that compare distributed inference (vLLM + LLM-D) against standard monolithic serving. This provides a tangible, side-by-side demonstration of the infrastructure efficiency gains from deploying disaggregated inference on OpenShift AI.

# Supply Chain Dashboard — Helm chart

Umbrella chart for the AI Supply Chain Agent quickstart. It deploys the application tier (backend, frontend, ingest job) plus shared AI/data subcharts from [ai-architecture-charts](https://github.com/rh-ai-quickstart/ai-architecture-charts).

## What it deploys

- **pgvector** — PostgreSQL with the pgvector extension
- **llama-stack** — Llama Stack API (chat, vector stores)
- **llm-service** — Model serving (e.g. Llama 3.2 1B)
- **backend** — Flask API
- **frontend** — React dashboard (nginx)
- **ingest** — Optional post-install Job (`ingest.enabled`)

## Prerequisites

- Helm 3.14+
- OpenShift CLI (`oc`) for cluster deploys
- A [Hugging Face token](https://huggingface.co/settings/tokens) (required for gated models)

## Provide the Hugging Face token

The `llm-service` sub-chart reads the token from a Secret named `huggingface-secret` (key `HF_TOKEN`).

**Option A — use `helm/secrets.yaml`** (recommended for local development):

1. Copy the example file and edit:

```bash
cp helm/secrets.example.yaml helm/secrets.yaml
# Edit helm/secrets.yaml and add your HF token
```

2. Deploy as usual — the Makefile automatically applies `helm/secrets.yaml` if it exists:

```bash
make helm-install
```

**Option B — set it in `values.yaml`** (not recommended):

```yaml
llm-service:
  secret:
    hf_token: "<your-hf-token>"
```

**Option C — pre-create the Secret** (recommended for production; the token never touches a values file or secrets.yaml):

```bash
oc create secret generic huggingface-secret \
  -n supply-chain-dashboard \
  --from-literal=HF_TOKEN="<your-hf-token>"
```

## Install

From the repository root:

```bash
helm dependency update ./helm
helm upgrade --install supply-chain-dashboard ./helm \
  -f helm/values.yaml \
  --namespace supply-chain-dashboard \
  --create-namespace \
  --wait \
  --timeout 10m
```

Or use `make helm-deps` and `make helm-install` (see root `Makefile`).

## Verify

```bash
oc get pods,route -n supply-chain-dashboard
```

## Customize

- **Models** — `global.models` and `llm-service.models`
- **GPU** — `llm-service.device` and per-model `device` (default is CPU in `values.yaml`)
- **Ingest** — `ingest.strategy` (`llamastack` | `langchain`), `ingest.enabled`, chunking under `ingest.*` for LangChain only

Full operator documentation: [README.md](../README.md) and [docs/WHAT_TO_EXPECT.md](../docs/WHAT_TO_EXPECT.md).

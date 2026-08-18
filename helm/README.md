# Supply Chain Dashboard — Helm chart

Umbrella chart for the AI Supply Chain Agent quickstart. It deploys the application tier (backend, frontend, ingest job) and the [general-simulation](https://github.com/robertsandoval/general-simulation) **0.0.1** platform subchart (Postgres, Neo4j, Llama Stack, llm-service, API, ingestion).

## What it deploys

- **general-simulation** — Postgres, Neo4j, Llama Stack, llm-service, bootstrap, API (optional ingestion CronJob)
- **backend** — Flask API (Llama Stack + gen-sim API clients)
- **frontend** — React dashboard (nginx)
- **ingest** — Optional post-install Job (`ingest.enabled`)

**Model selection is owned by gen-sim.** Configure providers under `general-simulation.global.models`, `general-simulation.llm-service`, and set the canonical stack model id on `general-simulation.api.models.generation`. The supply-chain backend sets `LLAMA_STACK_MODEL` from that value — it does not implement its own provider logic.

For a full visual map of every gen-sim value (defaults, supply-chain overrides, and credential sync), see [`docs/GEN_SIM_VALUES_MAPPING.md`](../docs/GEN_SIM_VALUES_MAPPING.md).

## Prerequisites

- Helm 3.14+
- OpenShift CLI (`oc`) for cluster deploys
- OpenShift AI 3.4+ (KServe) for default `llm-service`
- Hugging Face token: `general-simulation.llm-service.secret.hf_token` in `helm/secrets.yaml`

## Provide the Hugging Face token (default)

```bash
cp helm/secrets.example.yaml helm/secrets.yaml
# Set general-simulation.llm-service.secret.hf_token
make helm-install REGISTRY=quay.io/<your-org>
```

## Configure models (gen-sim only)

Change the model under `general-simulation` in `values.yaml` or via `--set`, for example:

```yaml
general-simulation:
  global:
    models:
      deepseek-r1-distill-qwen-1-5b:
        enabled: true
        id: deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
        apiToken: unused
      llama-3-2-3b-instruct:
        enabled: false
  llm-service:
    models:
      deepseek-r1-distill-qwen-1-5b:
        enabled: true
        id: deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
  api:
    models:
      generation: deepseek-r1-distill-qwen-1-5b/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
```

The backend automatically uses `general-simulation.api.models.generation` for chat.

## Optional: external MaaS

Disable `llm-service`, enable `general-simulation.global.models.external-model`, set `apiToken`, and set `general-simulation.api.models.generation` to `external-model/<id>`.

## Install

```bash
helm dependency update ./helm

# Point all images (supply-chain + gen-sim) at your registry:
helm upgrade --install supply-chain-dashboard ./helm \
  -f helm/values.yaml \
  -f helm/secrets.yaml \
  --namespace supply-chain-dashboard \
  --create-namespace \
  --set global.registry=quay.io/<your-org> \
  --wait --timeout 15m
```

Or via Make: `make helm-upgrade-install REGISTRY=quay.io/<your-org>`

## Verify

```bash
oc get pods,svc,inferenceservice -n supply-chain-dashboard

# Neo4j (gen-sim umbrella creates Secret/neo4j-auth, SA/neo4j-sa, and STS/neo4j):
oc get secret neo4j-auth sa/neo4j-sa sts/neo4j svc/neo4j -n supply-chain-dashboard
```

`values.yaml` sets demo Neo4j passwords on `general-simulation.bootstrap.neo4j.password` and matching `api`/`ingestion` blocks (required for Secret `neo4j-auth`). Override via `helm/secrets.yaml` — see `secrets.example.yaml`.

## Kind / local Kubernetes smoke

CI and local developers can install with `helm/values-kind.yaml` (disables OpenShift Routes, llama-stack, llm-service, and heavy ingestion). Supply-chain images are built into a local registry (`localhost:5001`) via per-component `image.repository` flags (`HELM_KIND_IMAGE_SETS`); platform images use `general-simulation.global.registry` in `values-kind.yaml`.

| Environment | Minimum RAM | Notes |
|-------------|-------------|-------|
| GHA `ubuntu-latest` | ~7Gi allocatable | Used by `.github/workflows/kind-helm-smoke.yml` |
| Local Podman + Kind | **8Gi Podman VM** | Neo4j requests 2Gi (official chart minimum) |

Neo4j cannot be reduced below 2Gi per the upstream `neo4j/neo4j` chart. Disabling Neo4j would break `general-sim-api` and the scenarios integration test.

```bash
make kind-preflight                    # check Podman VM / Kind node RAM (local only)
make local-kind-smoke-test             # cluster + build + helm-install-kind + verify
make local-kind-smoke-test LOCAL_KIND_SMOKE_ARGS='--recreate --skip-build'
```

If preflight fails on a 2Gi Podman machine, resize before recreating the cluster:

```bash
podman machine stop
podman machine set --memory 8192
podman machine start
make local-kind-smoke-test LOCAL_KIND_SMOKE_ARGS='--recreate --skip-build'
```

Full docs: [README.md](../README.md).

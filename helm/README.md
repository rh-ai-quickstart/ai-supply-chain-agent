# Example Helm Chart

This chart deploys:

- `pgvector` (PostgreSQL + vector extension)
- `llama-stack` configured to use `pgvector`
- A simple default model via `global.models`

## Prerequisites

- Helm 3.x
- OpenShift CLI (`oc`)
- Access to a cluster namespace/project

## Install

```bash
cd base_project/example
helm dependency update
oc new-project example-ai || oc project example-ai
helm upgrade --install example . -n example-ai
```

## Verify

```bash
oc get pods -n example-ai
oc get svc -n example-ai
```

## Customize model

Update `values.yaml` under `global.models` to enable/disable models or add your own entries using the same structure as the `llama-stack` chart.

#!/usr/bin/env bash
# OpenShift prod install with external LiteMaaS / MaaS model configuration.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"

NAMESPACE="${NAMESPACE:-supply-chain-dashboard}"
HELM_RELEASE="${HELM_RELEASE:-supply-chain-dashboard}"
HELM_CHART="${HELM_CHART:-./helm}"
REGISTRY="${REGISTRY:-quay.io/rh-ai-quickstart}"
BACKEND_TAG="${BACKEND_TAG:-dev}"
FRONTEND_TAG="${FRONTEND_TAG:-dev}"
INGEST_TAG="${INGEST_TAG:-dev}"
LLM_ID="${LLM_ID:-Qwen2.5-VL-7B-Instruct}"
VALUES_FILE="${VALUES_FILE:-${HELM_CHART}/values.yaml}"
SECRETS_FILE="${SECRETS_FILE:-${HELM_CHART}/secrets.yaml}"

log() { echo ">>> $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

test -n "${LLM_URL:-}" || fail "LLM_URL is required"
test -n "${LLM_API_TOKEN:-}" || fail "LLM_API_TOKEN is required"
test -n "${LLM_ID}" || fail "LLM_ID is required"

EMBED_BASE_URL="${EMBED_BASE_URL:-$(echo "${LLM_URL}" | sed 's#/v1/*$##')}"
GEN_MODEL="external-model/${LLM_ID}"

SECRETS_FLAGS=()
if [[ -f "${SECRETS_FILE}" ]]; then
  SECRETS_FLAGS=(-f "${SECRETS_FILE}")
fi

log "Updating Helm dependencies"
make helm-deps HELM_CHART="${HELM_CHART}"

log "Deploying ${HELM_RELEASE} to namespace ${NAMESPACE} (images tag=${BACKEND_TAG})"
log "LLM: ${GEN_MODEL} @ ${LLM_URL}"

if command -v oc >/dev/null 2>&1; then
  oc get namespace "${NAMESPACE}" >/dev/null 2>&1 || oc new-project "${NAMESPACE}"
fi

helm upgrade --install "${HELM_RELEASE}" "${HELM_CHART}" \
  --namespace "${NAMESPACE}" \
  --create-namespace \
  -f "${VALUES_FILE}" \
  "${SECRETS_FLAGS[@]}" \
  --set "global.registry=${REGISTRY}" \
  --set "global.imageTag=${BACKEND_TAG}" \
  --set "backend.image.tag=${BACKEND_TAG}" \
  --set "frontend.image.tag=${FRONTEND_TAG}" \
  --set "ingest.image.tag=${INGEST_TAG}" \
  --set "general-simulation.llm-service.enabled=false" \
  --set "general-simulation.global.models.external-model.enabled=true" \
  --set "general-simulation.global.models.external-model.id=${LLM_ID}" \
  --set "general-simulation.global.models.external-model.url=${LLM_URL}" \
  --set "general-simulation.global.models.external-model.apiToken=${LLM_API_TOKEN}" \
  --set "general-simulation.api.models.generation=${GEN_MODEL}" \
  --set "general-simulation.ingestion.models.generation=${GEN_MODEL}" \
  --set "backend.env.EMBED_API_KEY=${LLM_API_TOKEN}" \
  --set "backend.env.EMBED_BASE_URL=${EMBED_BASE_URL}" \
  ${HELM_EXTRA_ARGS:-} \
  --wait \
  --timeout 15m

log "Helm install complete."

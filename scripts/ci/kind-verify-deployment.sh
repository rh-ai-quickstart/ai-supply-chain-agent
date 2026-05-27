#!/usr/bin/env bash
# Post-deploy checks for Kind + Helm install (used by kind-helm-smoke workflow).
set -euo pipefail

NAMESPACE="${NAMESPACE:-supply-chain-dashboard}"
HELM_RELEASE="${HELM_RELEASE:-supply-chain-dashboard}"
BACKEND_PF_PORT="${BACKEND_PF_PORT:-15001}"
FRONTEND_PF_PORT="${FRONTEND_PF_PORT:-18080}"
CURL_MAX_TIME="${CURL_MAX_TIME:-120}"

log() { echo ">>> $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

# Avoid `echo … | grep -q` under pipefail (grep -q closes the pipe → SIGPIPE → false failure).
body_contains() {
  local needle="$1"
  local body="$2"
  [[ "${body}" == *"${needle}"* ]]
}

body_contains_ci() {
  local needle="${1,,}"
  local body="${2,,}"
  [[ "${body}" == *"${needle}"* ]]
}

cleanup() {
  for pid in "${BACKEND_PF_PID:-}" "${FRONTEND_PF_PID:-}"; do
    if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT

wait_for_url() {
  local url="$1"
  local attempts="${2:-30}"
  local i
  for i in $(seq 1 "${attempts}"); do
    if curl -sf --max-time "${CURL_MAX_TIME}" "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

curl_body() {
  local url="$1"
  curl -sf --max-time "${CURL_MAX_TIME}" "${url}"
}

# /api/v1/state calls OpenSky (8s timeout) on cold start; retry until kpis appear.
wait_for_dashboard_state() {
  local url="$1"
  local attempts="${2:-30}"
  local i body
  for i in $(seq 1 "${attempts}"); do
    if body=$(curl_body "${url}" 2>/dev/null) && body_contains "kpis" "${body}"; then
      echo "${body}"
      return 0
    fi
    sleep 2
  done
  return 1
}

log "Helm release status"
helm status "${HELM_RELEASE}" --namespace "${NAMESPACE}"

log "Workloads in namespace ${NAMESPACE}"
kubectl get deploy,svc,pods -n "${NAMESPACE}"

log "Expect backend and frontend Deployments Available"
kubectl wait -n "${NAMESPACE}" --for=condition=available \
  "deployment/${HELM_RELEASE}-backend" --timeout=120s
kubectl wait -n "${NAMESPACE}" --for=condition=available \
  "deployment/${HELM_RELEASE}-frontend" --timeout=120s

if kubectl get deployment pgvector -n "${NAMESPACE}" >/dev/null 2>&1; then
  log "Waiting for pgvector Deployment"
  kubectl wait -n "${NAMESPACE}" --for=condition=available deployment/pgvector --timeout=300s
fi

log "Port-forward backend Service"
kubectl port-forward -n "${NAMESPACE}" "svc/${HELM_RELEASE}-backend" \
  "${BACKEND_PF_PORT}:5001" >/tmp/kind-pf-backend.log 2>&1 &
BACKEND_PF_PID=$!
wait_for_url "http://127.0.0.1:${BACKEND_PF_PORT}/healthz" 30 \
  || fail "backend /healthz not ready (see /tmp/kind-pf-backend.log)"

HEALTH=$(curl_body "http://127.0.0.1:${BACKEND_PF_PORT}/healthz")
body_contains '"ok"' "${HEALTH}" || fail "unexpected /healthz body: ${HEALTH}"
log "PASS backend GET /healthz"

STATE=$(wait_for_dashboard_state "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/state" 30) \
  || fail "GET /api/v1/state not ready or missing kpis (OpenSky may be slow; see backend logs)"
log "PASS backend GET /api/v1/state"

GUARD=$(curl -sf --max-time "${CURL_MAX_TIME}" -X POST "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{"input":"Where is the best pizza?","chat_history":[]}')
body_contains 'answer' "${GUARD}" || fail "POST /api/v1/chat (guardrail) missing answer"
body_contains_ci 'supply chain' "${GUARD}" || fail "guardrail response unexpected: ${GUARD}"
log "PASS backend POST /api/v1/chat (off-topic guardrail)"

ROUTE=$(curl -sf --max-time "${CURL_MAX_TIME}" -X POST "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{"input":"Find the best truck route","chat_history":[]}')
body_contains 'routeData' "${ROUTE}" || fail "route chat response missing routeData: ${ROUTE}"
log "PASS backend POST /api/v1/chat (route optimization)"

log "Port-forward frontend Service"
kubectl port-forward -n "${NAMESPACE}" "svc/${HELM_RELEASE}-frontend" \
  "${FRONTEND_PF_PORT}:8080" >/tmp/kind-pf-frontend.log 2>&1 &
FRONTEND_PF_PID=$!
wait_for_url "http://127.0.0.1:${FRONTEND_PF_PORT}/" 30 \
  || fail "frontend / not ready (see /tmp/kind-pf-frontend.log)"

INDEX=$(curl_body "http://127.0.0.1:${FRONTEND_PF_PORT}/")
body_contains '<html' "${INDEX}" || fail "frontend index does not look like HTML"
log "PASS frontend GET / (SPA shell)"

PROXY_STATE=$(wait_for_dashboard_state "http://127.0.0.1:${FRONTEND_PF_PORT}/api/v1/state" 30) \
  || fail "frontend /api proxy failed: ${PROXY_STATE}"
log "PASS frontend GET /api/v1/state (nginx same-origin proxy)"

if [[ "${RUN_UI_E2E:-}" == "1" || "${RUN_UI_E2E:-}" == "true" ]]; then
  log "Running Playwright UI E2E tests"
  if ! python -m pytest --version >/dev/null 2>&1; then
    fail "pytest not found; install with: make e2e-ui-install"
  fi
  export SUPPLY_CHAIN_UI_ENDPOINT="http://127.0.0.1:${FRONTEND_PF_PORT}"
  export BACKEND_HEALTH_URL="http://127.0.0.1:${BACKEND_PF_PORT}/healthz"
  # Kind values disable Llama Stack; guardrail/route UI tests do not need the LLM.
  export SKIP_MODEL_TESTS="${SKIP_MODEL_TESTS:-true}"
  python -m pytest tests/e2e_ui/ -v --tb=short --browser chromium \
    || fail "Playwright UI E2E tests failed"
  log "PASS Playwright UI E2E"
fi

log "All Kind deployment verification checks passed."

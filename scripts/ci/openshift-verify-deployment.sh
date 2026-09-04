#!/usr/bin/env bash
# Post-deploy API (+ optional Playwright) checks for OpenShift nightly CI.
# Longer timeouts than kind-verify-deployment.sh for cold Llama Stack startup.
set -euo pipefail

NAMESPACE="${NAMESPACE:-supply-chain-dashboard}"
HELM_RELEASE="${HELM_RELEASE:-supply-chain-dashboard}"
BACKEND_PF_PORT="${BACKEND_PF_PORT:-15001}"
FRONTEND_PF_PORT="${FRONTEND_PF_PORT:-18080}"
CURL_MAX_TIME="${CURL_MAX_TIME:-120}"
DEPLOY_WAIT_TIMEOUT="${DEPLOY_WAIT_TIMEOUT:-900}"
WAIT_ATTEMPTS="${WAIT_ATTEMPTS:-450}"
KUBE="${KUBE:-oc}"

log() { echo ">>> $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

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
  local attempts="${2:-${WAIT_ATTEMPTS}}"
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

wait_for_body_contains() {
  local url="$1"
  local needle="$2"
  local attempts="${3:-${WAIT_ATTEMPTS}}"
  local i body
  for i in $(seq 1 "${attempts}"); do
    if body=$(curl_body "${url}" 2>/dev/null) && body_contains "${needle}" "${body}"; then
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
"${KUBE}" get deploy,svc,pods -n "${NAMESPACE}"

log "Expect backend and frontend Deployments Available (timeout ${DEPLOY_WAIT_TIMEOUT}s)"
"${KUBE}" wait -n "${NAMESPACE}" --for=condition=available \
  "deployment/${HELM_RELEASE}-backend" --timeout="${DEPLOY_WAIT_TIMEOUT}s"
"${KUBE}" wait -n "${NAMESPACE}" --for=condition=available \
  "deployment/${HELM_RELEASE}-frontend" --timeout="${DEPLOY_WAIT_TIMEOUT}s"

log "Port-forward backend Service"
"${KUBE}" port-forward -n "${NAMESPACE}" "svc/${HELM_RELEASE}-backend" \
  "${BACKEND_PF_PORT}:5001" >/tmp/openshift-pf-backend.log 2>&1 &
BACKEND_PF_PID=$!
wait_for_url "http://127.0.0.1:${BACKEND_PF_PORT}/healthz" \
  || fail "backend /healthz not ready (see /tmp/openshift-pf-backend.log)"

HEALTH=$(curl_body "http://127.0.0.1:${BACKEND_PF_PORT}/healthz")
body_contains '"ok"' "${HEALTH}" || fail "unexpected /healthz body: ${HEALTH}"
log "PASS backend GET /healthz"

VERSION=$(curl_body "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/version")
body_contains 'git_commit' "${VERSION}" || fail "unexpected /api/v1/version body: ${VERSION}"
log "PASS backend GET /api/v1/version"

SCENARIOS=$(wait_for_body_contains \
  "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/general-simulation/scenarios" "scenarios" 60) \
  || fail "GET /api/v1/general-simulation/scenarios not ready (see backend / gen-sim logs)"
log "PASS backend GET /api/v1/general-simulation/scenarios"

GUARD=$(curl -sf --max-time "${CURL_MAX_TIME}" -X POST "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{"input":"Where is the best pizza?","chat_history":[]}')
body_contains 'answer' "${GUARD}" || fail "POST /api/v1/chat (guardrail) missing answer"
body_contains_ci 'supply chain' "${GUARD}" || fail "guardrail response unexpected: ${GUARD}"
log "PASS backend POST /api/v1/chat (off-topic guardrail)"

log "Port-forward frontend Service"
"${KUBE}" port-forward -n "${NAMESPACE}" "svc/${HELM_RELEASE}-frontend" \
  "${FRONTEND_PF_PORT}:8080" >/tmp/openshift-pf-frontend.log 2>&1 &
FRONTEND_PF_PID=$!
wait_for_url "http://127.0.0.1:${FRONTEND_PF_PORT}/" \
  || fail "frontend / not ready (see /tmp/openshift-pf-frontend.log)"

INDEX=$(curl_body "http://127.0.0.1:${FRONTEND_PF_PORT}/")
body_contains '<html' "${INDEX}" || fail "frontend index does not look like HTML"
log "PASS frontend GET / (SPA shell)"

PROXY_VERSION=$(wait_for_body_contains \
  "http://127.0.0.1:${FRONTEND_PF_PORT}/api/v1/version" "git_commit" 60) \
  || fail "frontend /api proxy failed: ${PROXY_VERSION}"
log "PASS frontend GET /api/v1/version (nginx same-origin proxy)"

if [[ "${RUN_UI_E2E:-}" == "1" || "${RUN_UI_E2E:-}" == "true" ]]; then
  log "Running Playwright UI E2E tests"
  if ! python -m pytest --version >/dev/null 2>&1; then
    fail "pytest not found; install with: make e2e-ui-install"
  fi
  export SUPPLY_CHAIN_UI_ENDPOINT="http://127.0.0.1:${FRONTEND_PF_PORT}"
  export BACKEND_HEALTH_URL="http://127.0.0.1:${BACKEND_PF_PORT}/healthz"
  export SKIP_MODEL_TESTS="${SKIP_MODEL_TESTS:-false}"
  export E2E_CHAT_TIMEOUT_MS="${E2E_CHAT_TIMEOUT_MS:-120000}"
  python -m pytest tests/e2e_ui/ -v --tb=short --browser chromium \
    || fail "Playwright UI E2E tests failed"
  log "PASS Playwright UI E2E"
fi

log "All OpenShift deployment verification checks passed."

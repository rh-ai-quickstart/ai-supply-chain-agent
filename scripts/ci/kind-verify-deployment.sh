#!/usr/bin/env bash
# Post-deploy checks for Kind + Helm install (used by kind-helm-smoke workflow).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

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

# Retry until the response body contains a needle (gen-sim / proxy warm-up).
wait_for_body_contains() {
  local url="$1"
  local needle="$2"
  local attempts="${3:-30}"
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

seed_gen_sim_demo() {
  local seed_script="${ROOT_DIR}/scripts/ci/kind-seed-demo-scenarios.py"
  log "Seeding general-simulation demo scenarios for UI E2E (Neo4j direct)"
  kubectl wait -n "${NAMESPACE}" --for=condition=available \
    deployment/general-sim-api --timeout=120s
  [[ -f "${seed_script}" ]] || fail "missing seed script: ${seed_script}"

  if ! kubectl exec -i -n "${NAMESPACE}" deploy/general-sim-api -- \
    python - < "${seed_script}"; then
    fail "Neo4j scenario seed failed (see general-sim-api logs)"
  fi

  wait_for_body_contains \
    "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/general-simulation/scenarios" \
    "opensky-uk-closure-001" 30 \
    || fail "Demo scenarios not visible after seed (expected opensky-uk-closure-001)"
  log "PASS general-simulation demo scenario seed (opensky-uk-closure-001)"
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

log "Port-forward backend Service"
kubectl port-forward -n "${NAMESPACE}" "svc/${HELM_RELEASE}-backend" \
  "${BACKEND_PF_PORT}:5001" >/tmp/kind-pf-backend.log 2>&1 &
BACKEND_PF_PID=$!
wait_for_url "http://127.0.0.1:${BACKEND_PF_PORT}/healthz" 30 \
  || fail "backend /healthz not ready (see /tmp/kind-pf-backend.log)"

HEALTH=$(curl_body "http://127.0.0.1:${BACKEND_PF_PORT}/healthz")
body_contains '"ok"' "${HEALTH}" || fail "unexpected /healthz body: ${HEALTH}"
log "PASS backend GET /healthz"

VERSION=$(curl_body "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/version")
body_contains 'git_commit' "${VERSION}" || fail "unexpected /api/v1/version body: ${VERSION}"
log "PASS backend GET /api/v1/version"

SCENARIOS=$(wait_for_body_contains \
  "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/general-simulation/scenarios" "scenarios" 30) \
  || fail "GET /api/v1/general-simulation/scenarios not ready (see backend / gen-sim logs)"
log "PASS backend GET /api/v1/general-simulation/scenarios"

GUARD=$(curl -sf --max-time "${CURL_MAX_TIME}" -X POST "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{"input":"Where is the best pizza?","chat_history":[]}')
body_contains 'answer' "${GUARD}" || fail "POST /api/v1/chat (guardrail) missing answer"
body_contains_ci 'supply chain' "${GUARD}" || fail "guardrail response unexpected: ${GUARD}"
log "PASS backend POST /api/v1/chat (off-topic guardrail)"

log "Port-forward frontend Service"
kubectl port-forward -n "${NAMESPACE}" "svc/${HELM_RELEASE}-frontend" \
  "${FRONTEND_PF_PORT}:8080" >/tmp/kind-pf-frontend.log 2>&1 &
FRONTEND_PF_PID=$!
wait_for_url "http://127.0.0.1:${FRONTEND_PF_PORT}/" 30 \
  || fail "frontend / not ready (see /tmp/kind-pf-frontend.log)"

INDEX=$(curl_body "http://127.0.0.1:${FRONTEND_PF_PORT}/")
body_contains '<html' "${INDEX}" || fail "frontend index does not look like HTML"
log "PASS frontend GET / (SPA shell)"

PROXY_VERSION=$(wait_for_body_contains \
  "http://127.0.0.1:${FRONTEND_PF_PORT}/api/v1/version" "git_commit" 30) \
  || fail "frontend /api proxy failed: ${PROXY_VERSION}"
log "PASS frontend GET /api/v1/version (nginx same-origin proxy)"

if [[ "${RUN_UI_E2E:-}" == "1" || "${RUN_UI_E2E:-}" == "true" ]]; then
  seed_gen_sim_demo
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

#!/usr/bin/env bash
# Post-deploy checks for Kind + Helm install (used by kind-helm-smoke workflow).
set -euo pipefail

NAMESPACE="${NAMESPACE:-supply-chain-dashboard}"
HELM_RELEASE="${HELM_RELEASE:-supply-chain-dashboard}"
BACKEND_PF_PORT="${BACKEND_PF_PORT:-15001}"
FRONTEND_PF_PORT="${FRONTEND_PF_PORT:-18080}"

log() { echo ">>> $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

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
    if curl -sf "${url}" >/dev/null 2>&1; then
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

HEALTH=$(curl -sf "http://127.0.0.1:${BACKEND_PF_PORT}/healthz")
echo "${HEALTH}" | grep -q '"ok"' || fail "unexpected /healthz body: ${HEALTH}"
log "PASS backend GET /healthz"

STATE=$(curl -sf "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/state")
echo "${STATE}" | grep -q 'kpis' || fail "GET /api/v1/state missing kpis key"
log "PASS backend GET /api/v1/state"

GUARD=$(curl -sf -X POST "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{"input":"Where is the best pizza?","chat_history":[]}')
echo "${GUARD}" | grep -q 'answer' || fail "POST /api/v1/chat (guardrail) missing answer"
echo "${GUARD}" | grep -qi 'supply chain' || fail "guardrail response unexpected: ${GUARD}"
log "PASS backend POST /api/v1/chat (off-topic guardrail)"

ROUTE=$(curl -sf -X POST "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d '{"input":"Find the best truck route","chat_history":[]}')
echo "${ROUTE}" | grep -q 'routeData' || fail "route chat response missing routeData: ${ROUTE}"
log "PASS backend POST /api/v1/chat (route optimization)"

log "Port-forward frontend Service"
kubectl port-forward -n "${NAMESPACE}" "svc/${HELM_RELEASE}-frontend" \
  "${FRONTEND_PF_PORT}:8080" >/tmp/kind-pf-frontend.log 2>&1 &
FRONTEND_PF_PID=$!
wait_for_url "http://127.0.0.1:${FRONTEND_PF_PORT}/" 30 \
  || fail "frontend / not ready (see /tmp/kind-pf-frontend.log)"

INDEX=$(curl -sf "http://127.0.0.1:${FRONTEND_PF_PORT}/")
echo "${INDEX}" | grep -qi '<html' || fail "frontend index does not look like HTML"
log "PASS frontend GET / (SPA shell)"

PROXY_STATE=$(curl -sf "http://127.0.0.1:${FRONTEND_PF_PORT}/api/v1/state")
echo "${PROXY_STATE}" | grep -q 'kpis' || fail "frontend /api proxy failed: ${PROXY_STATE}"
log "PASS frontend GET /api/v1/state (nginx same-origin proxy)"

log "All Kind deployment verification checks passed."

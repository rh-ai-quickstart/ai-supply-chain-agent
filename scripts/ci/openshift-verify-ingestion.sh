#!/usr/bin/env bash
# Verify Helm post-install ingest Job and vector store listing on OpenShift.
set -euo pipefail

NAMESPACE="${NAMESPACE:-supply-chain-dashboard}"
HELM_RELEASE="${HELM_RELEASE:-supply-chain-dashboard}"
BACKEND_PF_PORT="${BACKEND_PF_PORT:-15001}"
INGEST_WAIT_TIMEOUT="${INGEST_WAIT_TIMEOUT:-900}"
CURL_MAX_TIME="${CURL_MAX_TIME:-120}"
WAIT_ATTEMPTS="${WAIT_ATTEMPTS:-60}"
KUBE="${KUBE:-oc}"

log() { echo ">>> $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

cleanup() {
  if [ -n "${BACKEND_PF_PID:-}" ] && kill -0 "${BACKEND_PF_PID}" 2>/dev/null; then
    kill "${BACKEND_PF_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

INGEST_JOB="${HELM_RELEASE}-ingest"

log "Waiting for ingest Job ${INGEST_JOB} to complete (timeout ${INGEST_WAIT_TIMEOUT}s)"
if ! "${KUBE}" wait -n "${NAMESPACE}" --for=condition=complete \
  "job/${INGEST_JOB}" --timeout="${INGEST_WAIT_TIMEOUT}s"; then
  log "Ingest Job did not complete — dumping logs"
  "${KUBE}" logs "job/${INGEST_JOB}" -n "${NAMESPACE}" --all-containers --tail=200 || true
  "${KUBE}" describe "job/${INGEST_JOB}" -n "${NAMESPACE}" || true
  fail "ingest Job ${INGEST_JOB} failed or timed out"
fi
log "PASS ingest Job ${INGEST_JOB} completed"

log "Port-forward backend for vector_stores check"
"${KUBE}" port-forward -n "${NAMESPACE}" "svc/${HELM_RELEASE}-backend" \
  "${BACKEND_PF_PORT}:5001" >/tmp/openshift-pf-ingest-backend.log 2>&1 &
BACKEND_PF_PID=$!

for i in $(seq 1 "${WAIT_ATTEMPTS}"); do
  if curl -sf --max-time "${CURL_MAX_TIME}" \
    "http://127.0.0.1:${BACKEND_PF_PORT}/healthz" >/dev/null 2>&1; then
    break
  fi
  if [ "${i}" -eq "${WAIT_ATTEMPTS}" ]; then
    fail "backend not reachable for vector_stores check (see /tmp/openshift-pf-ingest-backend.log)"
  fi
  sleep 2
done

BODY=$(curl -sf --max-time "${CURL_MAX_TIME}" \
  "http://127.0.0.1:${BACKEND_PF_PORT}/api/v1/vector_stores")
if [[ "${BODY}" != *"vector_stores"* ]]; then
  fail "unexpected /api/v1/vector_stores body: ${BODY}"
fi
if [[ "${BODY}" == *'"vector_stores":[]'* ]] || [[ "${BODY}" == *'"vector_stores": []'* ]]; then
  fail "vector_stores list is empty after ingest — body: ${BODY}"
fi
log "PASS backend GET /api/v1/vector_stores (non-empty)"
log "Ingestion verification passed."

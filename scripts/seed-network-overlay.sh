#!/usr/bin/env bash
# Merge supply-chain-network.yaml into gen-sim Postgres + Neo4j via port-forward.
#
# Run after seed-gen-sim-demo.sh (base demo must exist first).
#
# Usage:
#   ./scripts/seed-network-overlay.sh
#   NETWORK_YAML=/path/to/network.yaml make seed-network-overlay
#
# Overrides:
#   NAMESPACE / GEN_SIM_NAMESPACE  OpenShift project (auto-detected if unset)
#   GENERAL_SIM_DIR                Path to general-simulation checkout
#   NETWORK_YAML                   Overlay YAML (default: data/supply-chain-network.yaml)
#   LOCAL_NEO4J_PORT               Default 7687
#   LOCAL_PG_PORT                  Default 5433
#   OC                             oc or kubectl binary (default: oc)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OC="${OC:-oc}"
LOCAL_NEO4J_PORT="${LOCAL_NEO4J_PORT:-7687}"
LOCAL_PG_PORT="${LOCAL_PG_PORT:-5433}"
GENERAL_SIM_DIR="${GENERAL_SIM_DIR:-${ROOT}/vendor/general-simulation}"
NETWORK_YAML="${NETWORK_YAML:-${ROOT}/data/supply-chain-network.yaml}"

log() { echo ">>> $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "'$1' is required but not on PATH"
}

ns_has_svc() {
  local ns="$1" svc="$2"
  "${OC}" get svc "${svc}" -n "${ns}" >/dev/null 2>&1
}

resolve_namespace() {
  if [[ -n "${GEN_SIM_NAMESPACE:-}" ]]; then
    echo "${GEN_SIM_NAMESPACE}"
    return
  fi
  if [[ -n "${NAMESPACE:-}" ]] && ns_has_svc "${NAMESPACE}" postgres && ns_has_svc "${NAMESPACE}" neo4j; then
    echo "${NAMESPACE}"
    return
  fi
  if ns_has_svc supply-chain-dashboard postgres && ns_has_svc supply-chain-dashboard neo4j; then
    echo supply-chain-dashboard
    return
  fi
  if ns_has_svc general-sim postgres && ns_has_svc general-sim neo4j; then
    echo general-sim
    return
  fi
  fail "Could not find postgres+neo4j Services. Set GEN_SIM_NAMESPACE=<ns>."
}

wait_for_port() {
  local port="$1" label="$2" tries=40
  local i=0
  while (( i < tries )); do
    if python3 -c "import socket; s=socket.create_connection(('127.0.0.1', ${port}), 0.5); s.close()" 2>/dev/null; then
      return 0
    fi
    sleep 0.25
    i=$((i + 1))
  done
  fail "Timed out waiting for local port ${port} (${label})"
}

neo4j_password_from_secret() {
  local ns="$1"
  local raw
  raw="$("${OC}" get secret neo4j-auth -n "${ns}" -o jsonpath='{.data.NEO4J_AUTH}' | base64 -d)"
  if [[ "${raw}" == */* ]]; then
    echo "${raw#*/}"
  else
    echo "${raw}"
  fi
}

postgres_dsn_from_secret() {
  local ns="$1" local_port="$2"
  local user password
  user="$("${OC}" get secret postgres-credentials -n "${ns}" -o jsonpath='{.data.username}' | base64 -d)"
  password="$("${OC}" get secret postgres-credentials -n "${ns}" -o jsonpath='{.data.password}' | base64 -d)"
  [[ -n "${user}" && -n "${password}" ]] || fail "postgres-credentials missing username/password in ${ns}"
  local enc
  enc="$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "${password}")"
  echo "postgresql://${user}:${enc}@127.0.0.1:${local_port}/sim"
}

run_overlay() {
  local sim_dir="$1" yaml_path="$2"
  cd "${sim_dir}"
  export NETWORK_YAML="${yaml_path}"
  if command -v uv >/dev/null 2>&1; then
    uv python install
    uv run python scripts/seed_network_overlay.py "${yaml_path}"
  elif [[ -x "${sim_dir}/.venv/bin/python" ]]; then
    NETWORK_YAML="${yaml_path}" "${sim_dir}/.venv/bin/python" scripts/seed_network_overlay.py "${yaml_path}"
  else
    NETWORK_YAML="${yaml_path}" python3 scripts/seed_network_overlay.py "${yaml_path}"
  fi
}

need_cmd "${OC}"
need_cmd python3
need_cmd base64

[[ -d "${GENERAL_SIM_DIR}" ]] || fail "general-simulation not found at ${GENERAL_SIM_DIR} (set GENERAL_SIM_DIR)"
[[ -f "${GENERAL_SIM_DIR}/scripts/seed_network_overlay.py" ]] || fail "Missing ${GENERAL_SIM_DIR}/scripts/seed_network_overlay.py"
[[ -f "${NETWORK_YAML}" ]] || fail "Network YAML not found at ${NETWORK_YAML}"

NS="$(resolve_namespace)"
log "Using namespace: ${NS}"
log "general-simulation: ${GENERAL_SIM_DIR}"
log "network overlay: ${NETWORK_YAML}"

"${OC}" get svc neo4j -n "${NS}" >/dev/null || fail "Service neo4j not found in ${NS}"
"${OC}" get svc postgres -n "${NS}" >/dev/null || fail "Service postgres not found in ${NS}"
"${OC}" get secret neo4j-auth -n "${NS}" >/dev/null || fail "Secret neo4j-auth not found in ${NS}"
"${OC}" get secret postgres-credentials -n "${NS}" >/dev/null || fail "Secret postgres-credentials not found in ${NS}"

NEO4J_PASSWORD="$(neo4j_password_from_secret "${NS}")"
POSTGRES_DSN="$(postgres_dsn_from_secret "${NS}" "${LOCAL_PG_PORT}")"
[[ -n "${NEO4J_PASSWORD}" ]] || fail "Empty Neo4j password from neo4j-auth"

PF_NEO4J_PID=""
PF_PG_PID=""
cleanup() {
  for pid in "${PF_NEO4J_PID}" "${PF_PG_PID}"; do
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
      wait "${pid}" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT

log "Port-forward neo4j ${LOCAL_NEO4J_PORT}:7687"
"${OC}" port-forward -n "${NS}" svc/neo4j "${LOCAL_NEO4J_PORT}:7687" >/dev/null 2>&1 &
PF_NEO4J_PID=$!

log "Port-forward postgres ${LOCAL_PG_PORT}:5432"
"${OC}" port-forward -n "${NS}" svc/postgres "${LOCAL_PG_PORT}:5432" >/dev/null 2>&1 &
PF_PG_PID=$!

wait_for_port "${LOCAL_NEO4J_PORT}" "neo4j"
wait_for_port "${LOCAL_PG_PORT}" "postgres"

export NEO4J_URI="bolt://127.0.0.1:${LOCAL_NEO4J_PORT}"
export NEO4J_USER="${NEO4J_USER:-neo4j}"
export NEO4J_PASSWORD
export POSTGRES_DSN

log "Merging network overlay into Neo4j + Postgres…"
run_overlay "${GENERAL_SIM_DIR}" "${NETWORK_YAML}"
log "Done."

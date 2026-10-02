#!/usr/bin/env bash
# Import network YAML files and, when enabled, live OpenSky flights.
#
# What runs is read from the Helm values file (`seed.networkFiles` and
# `seed.opensky`). YAML is merged first, then OpenSky, through one
# port-forward to cluster Postgres + Neo4j.
#
# OpenSky blocks many AWS/hyperscaler source IPs, so the HTTP pull stays on
# the laptop. Run `make seed-gen-sim` first for demo scenarios.
#
# Usage:
#   make seed-opensky
#   make seed-opensky GEN_SIM_NAMESPACE=supply-chain-dashboard
#   VALUES_FILE=helm/values.yaml ./scripts/seed-opensky.sh
#
# Overrides:
#   VALUES_FILE                     Helm values file (default: helm/values.yaml)
#   GEN_SIM_NAMESPACE / NAMESPACE   OpenShift project (auto-detected if unset)
#   GENERAL_SIM_DIR                 Path to general-simulation checkout
#   LOCAL_NEO4J_PORT / LOCAL_PG_PORT
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OC="${OC:-oc}"
LOCAL_NEO4J_PORT="${LOCAL_NEO4J_PORT:-7687}"
LOCAL_PG_PORT="${LOCAL_PG_PORT:-5433}"
GENERAL_SIM_DIR="${GENERAL_SIM_DIR:-${ROOT}/vendor/general-simulation}"
VALUES_FILE="${VALUES_FILE:-${ROOT}/helm/values.yaml}"

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
  fail "Could not find postgres+neo4j Services. Set GEN_SIM_NAMESPACE=supply-chain-dashboard."
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
  local user password enc
  user="$("${OC}" get secret postgres-credentials -n "${ns}" -o jsonpath='{.data.username}' | base64 -d)"
  password="$("${OC}" get secret postgres-credentials -n "${ns}" -o jsonpath='{.data.password}' | base64 -d)"
  [[ -n "${user}" && -n "${password}" ]] || fail "postgres-credentials missing username/password in ${ns}"
  enc="$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "${password}")"
  echo "postgresql://${user}:${enc}@127.0.0.1:${local_port}/sim"
}

# Run a Python entrypoint under uv, .venv, or system python3.
# Caller cds via the function; arguments are paths/flags passed to python.
run_gen_sim_python() {
  local sim_dir="$1"
  shift
  (
    cd "${sim_dir}"
    if command -v uv >/dev/null 2>&1; then
      uv run python "$@"
    elif [[ -x "${sim_dir}/.venv/bin/python" ]]; then
      "${sim_dir}/.venv/bin/python" "$@"
    else
      python3 "$@"
    fi
  )
}

resolve_values_file() {
  local path="$1"
  if [[ "${path}" = /* ]]; then
    printf '%s\n' "${path}"
    return
  fi
  local dir base
  dir="$(cd "$(dirname "${path}")" && pwd)"
  base="$(basename "${path}")"
  printf '%s\n' "${dir}/${base}"
}

need_cmd "${OC}"
need_cmd python3
need_cmd base64

[[ -d "${GENERAL_SIM_DIR}" ]] || fail "general-simulation not found at ${GENERAL_SIM_DIR} (set GENERAL_SIM_DIR)"
[[ -f "${ROOT}/scripts/read_seed_config.py" ]] || fail "Missing ${ROOT}/scripts/read_seed_config.py"

VALUES_FILE="$(resolve_values_file "${VALUES_FILE}")"

if command -v uv >/dev/null 2>&1; then
  # Explicit install works even when python-downloads=manual (e.g. Fedora's
  # packaged uv) — `uv run` alone would fail there if the pinned
  # .python-version isn't already present instead of downloading it.
  (cd "${GENERAL_SIM_DIR}" && uv python install)
fi

CONFIG_JSON="$(run_gen_sim_python "${GENERAL_SIM_DIR}" "${ROOT}/scripts/read_seed_config.py" "${ROOT}" "${VALUES_FILE}")" \
  || fail "Could not read seed config from ${VALUES_FILE}"

NETWORK_COUNT="$(python3 -c 'import json,sys; print(len(json.loads(sys.argv[1])["networkFiles"]))' "${CONFIG_JSON}")"
OPENSKY_ENABLED="$(python3 -c 'import json,sys; print("1" if json.loads(sys.argv[1])["opensky"]["enabled"] else "0")' "${CONFIG_JSON}")"
OPENSKY_MAX="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["opensky"]["max"])' "${CONFIG_JSON}")"
OPENSKY_TIMEOUT="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["opensky"]["timeoutSeconds"])' "${CONFIG_JSON}")"

if [[ "${NETWORK_COUNT}" -gt 0 ]]; then
  [[ -f "${GENERAL_SIM_DIR}/scripts/seed_network_overlay.py" ]] || fail "Missing ${GENERAL_SIM_DIR}/scripts/seed_network_overlay.py"
fi
if [[ "${OPENSKY_ENABLED}" == "1" ]]; then
  [[ -f "${GENERAL_SIM_DIR}/scripts/seed_opensky_live.py" ]] || fail "Missing ${GENERAL_SIM_DIR}/scripts/seed_opensky_live.py"
fi

log "Values file: ${VALUES_FILE}"
log "Network YAML files: ${NETWORK_COUNT}"
if [[ "${NETWORK_COUNT}" -gt 0 ]]; then
  python3 -c 'import json,sys; [print(p) for p in json.loads(sys.argv[1])["networkFiles"]]' "${CONFIG_JSON}" \
    | while IFS= read -r network_yaml; do
        log "  ${network_yaml}"
      done
fi
if [[ "${OPENSKY_ENABLED}" == "1" ]]; then
  log "OpenSky max entities: ${OPENSKY_MAX} (0 = unlimited)"
else
  log "OpenSky: disabled (seed.opensky.enabled is false)"
fi

NS="$(resolve_namespace)"
log "Using namespace: ${NS}"
log "general-simulation: ${GENERAL_SIM_DIR}"
log "Dashboard UI reads general-sim-api / Postgres in this namespace — use supply-chain-dashboard for the SPA."

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
export ENABLED_DOMAINS="${ENABLED_DOMAINS:-aviation}"

if [[ "${NETWORK_COUNT}" -gt 0 ]]; then
  while IFS= read -r network_yaml; do
    [[ -n "${network_yaml}" ]] || continue
    log "Merging network overlay: ${network_yaml}"
    run_gen_sim_python "${GENERAL_SIM_DIR}" scripts/seed_network_overlay.py "${network_yaml}"
  done < <(python3 -c 'import json,sys; [print(p) for p in json.loads(sys.argv[1])["networkFiles"]]' "${CONFIG_JSON}")
fi

if [[ "${OPENSKY_ENABLED}" == "1" ]]; then
  log "Fetching OpenSky on this laptop → upserting into cluster Postgres + Neo4j…"
  run_gen_sim_python "${GENERAL_SIM_DIR}" scripts/seed_opensky_live.py \
    --max "${OPENSKY_MAX}" \
    --timeout "${OPENSKY_TIMEOUT}"
fi

log "Done. Open Simulation (Live Flights map mode) after frontend rebuild to see flights."

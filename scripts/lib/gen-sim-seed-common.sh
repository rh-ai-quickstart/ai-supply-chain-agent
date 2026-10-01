#!/usr/bin/env bash
# Shared helpers for gen-sim laptop seed scripts (port-forward + cluster secrets).
# Sourced by seed-gen-sim-demo.sh, seed-network-overlay.sh, seed-opensky-live.sh.
#
# Expects caller to set ROOT before sourcing. Exports/uses:
#   OC, LOCAL_NEO4J_PORT, LOCAL_PG_PORT, GENERAL_SIM_DIR
#   PF_NEO4J_PID, PF_PG_PID (set by gen_sim_start_port_forwards)

: "${ROOT:?ROOT must be set before sourcing gen-sim-seed-common.sh}"

OC="${OC:-oc}"
LOCAL_NEO4J_PORT="${LOCAL_NEO4J_PORT:-7687}"
LOCAL_PG_PORT="${LOCAL_PG_PORT:-5433}"
GENERAL_SIM_DIR="${GENERAL_SIM_DIR:-${ROOT}/vendor/general-simulation}"

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
  local user password enc
  user="$("${OC}" get secret postgres-credentials -n "${ns}" -o jsonpath='{.data.username}' | base64 -d)"
  password="$("${OC}" get secret postgres-credentials -n "${ns}" -o jsonpath='{.data.password}' | base64 -d)"
  [[ -n "${user}" && -n "${password}" ]] || fail "postgres-credentials missing username/password in ${ns}"
  enc="$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "${password}")"
  echo "postgresql://${user}:${enc}@127.0.0.1:${local_port}/sim"
}

# Run a Python entrypoint under uv, .venv, or system python3.
# Usage: run_with_uv_or_venv <sim_dir> <script_relpath> [args...]
run_with_uv_or_venv() {
  local sim_dir="$1"
  local script_rel="$2"
  shift 2
  cd "${sim_dir}"
  if command -v uv >/dev/null 2>&1; then
    uv python install
    uv run python "${script_rel}" "$@"
  elif [[ -x "${sim_dir}/.venv/bin/python" ]]; then
    "${sim_dir}/.venv/bin/python" "${script_rel}" "$@"
  else
    python3 "${script_rel}" "$@"
  fi
}

gen_sim_require_cluster() {
  local ns="$1"
  "${OC}" get svc neo4j -n "${ns}" >/dev/null || fail "Service neo4j not found in ${ns}"
  "${OC}" get svc postgres -n "${ns}" >/dev/null || fail "Service postgres not found in ${ns}"
  "${OC}" get secret neo4j-auth -n "${ns}" >/dev/null || fail "Secret neo4j-auth not found in ${ns}"
  "${OC}" get secret postgres-credentials -n "${ns}" >/dev/null || fail "Secret postgres-credentials not found in ${ns}"
}

# Start neo4j + postgres port-forwards and export connection env.
# Sets PF_NEO4J_PID / PF_PG_PID and installs an EXIT trap to clean them up.
gen_sim_start_port_forwards() {
  local ns="$1"
  local neo4j_password postgres_dsn

  neo4j_password="$(neo4j_password_from_secret "${ns}")"
  postgres_dsn="$(postgres_dsn_from_secret "${ns}" "${LOCAL_PG_PORT}")"
  [[ -n "${neo4j_password}" ]] || fail "Empty Neo4j password from neo4j-auth"

  PF_NEO4J_PID=""
  PF_PG_PID=""
  gen_sim_cleanup_port_forwards() {
    for pid in "${PF_NEO4J_PID}" "${PF_PG_PID}"; do
      if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
        kill "${pid}" 2>/dev/null || true
        wait "${pid}" 2>/dev/null || true
      fi
    done
  }
  trap gen_sim_cleanup_port_forwards EXIT

  log "Port-forward neo4j ${LOCAL_NEO4J_PORT}:7687"
  "${OC}" port-forward -n "${ns}" svc/neo4j "${LOCAL_NEO4J_PORT}:7687" >/dev/null 2>&1 &
  PF_NEO4J_PID=$!

  log "Port-forward postgres ${LOCAL_PG_PORT}:5432"
  "${OC}" port-forward -n "${ns}" svc/postgres "${LOCAL_PG_PORT}:5432" >/dev/null 2>&1 &
  PF_PG_PID=$!

  wait_for_port "${LOCAL_NEO4J_PORT}" "neo4j"
  wait_for_port "${LOCAL_PG_PORT}" "postgres"

  export NEO4J_URI="bolt://127.0.0.1:${LOCAL_NEO4J_PORT}"
  export NEO4J_USER="${NEO4J_USER:-neo4j}"
  export NEO4J_PASSWORD="${neo4j_password}"
  export POSTGRES_DSN="${postgres_dsn}"
}

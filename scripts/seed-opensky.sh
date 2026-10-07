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
# shellcheck source=lib/gen-sim-seed-common.sh
source "${ROOT}/scripts/lib/gen-sim-seed-common.sh"

VALUES_FILE="${VALUES_FILE:-${ROOT}/helm/values.yaml}"

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

[[ -f "${ROOT}/scripts/read_seed_config.py" ]] || fail "Missing ${ROOT}/scripts/read_seed_config.py"

VALUES_FILE="$(resolve_values_file "${VALUES_FILE}")"

# Ensure gen-sim Python deps (PyYAML) are available before reading values.
if command -v uv >/dev/null 2>&1; then
  (cd "${GENERAL_SIM_DIR}" && uv python install)
fi

need_cmd python3
[[ -d "${GENERAL_SIM_DIR}" ]] || fail "general-simulation not found at ${GENERAL_SIM_DIR} (set GENERAL_SIM_DIR)"

CONFIG_JSON="$(
  (
    cd "${GENERAL_SIM_DIR}"
    if command -v uv >/dev/null 2>&1; then
      uv run python "${ROOT}/scripts/read_seed_config.py" "${ROOT}" "${VALUES_FILE}"
    elif [[ -x "${GENERAL_SIM_DIR}/.venv/bin/python" ]]; then
      "${GENERAL_SIM_DIR}/.venv/bin/python" "${ROOT}/scripts/read_seed_config.py" "${ROOT}" "${VALUES_FILE}"
    else
      python3 "${ROOT}/scripts/read_seed_config.py" "${ROOT}" "${VALUES_FILE}"
    fi
  )
)" || fail "Could not read seed config from ${VALUES_FILE}"

NETWORK_COUNT="$(python3 -c 'import json,sys; print(len(json.loads(sys.argv[1])["networkFiles"]))' "${CONFIG_JSON}")"
OPENSKY_ENABLED="$(python3 -c 'import json,sys; print("1" if json.loads(sys.argv[1])["opensky"]["enabled"] else "0")' "${CONFIG_JSON}")"
OPENSKY_MAX="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["opensky"]["max"])' "${CONFIG_JSON}")"
OPENSKY_TIMEOUT="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["opensky"]["timeoutSeconds"])' "${CONFIG_JSON}")"

if [[ "${NETWORK_COUNT}" -gt 0 ]]; then
  [[ -f "${GENERAL_SIM_DIR}/scripts/seed_network_overlay.py" ]] || fail \
    "Missing ${GENERAL_SIM_DIR}/scripts/seed_network_overlay.py (pin vendor/general-simulation to a commit that includes network YAML seeding, e.g. 07b4b4eb / feat/nested-cargo-yaml — not plain origin/development)"
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

# Prefer an entrypoint that exists so prepare_seed can validate the checkout.
if [[ "${NETWORK_COUNT}" -gt 0 ]]; then
  gen_sim_prepare_seed scripts/seed_network_overlay.py
elif [[ "${OPENSKY_ENABLED}" == "1" ]]; then
  gen_sim_prepare_seed scripts/seed_opensky_live.py
else
  fail "Nothing to seed (empty networkFiles and opensky disabled)"
fi

log "Dashboard UI reads general-sim-api / Postgres in this namespace — use supply-chain-dashboard for the SPA."
export ENABLED_DOMAINS="${ENABLED_DOMAINS:-aviation}"

if [[ "${NETWORK_COUNT}" -gt 0 ]]; then
  while IFS= read -r network_yaml; do
    [[ -n "${network_yaml}" ]] || continue
    log "Merging network overlay: ${network_yaml}"
    run_with_uv_or_venv "${GENERAL_SIM_DIR}" scripts/seed_network_overlay.py "${network_yaml}"
  done < <(python3 -c 'import json,sys; [print(p) for p in json.loads(sys.argv[1])["networkFiles"]]' "${CONFIG_JSON}")
fi

if [[ "${OPENSKY_ENABLED}" == "1" ]]; then
  log "Fetching OpenSky on this laptop → upserting into cluster Postgres + Neo4j…"
  run_with_uv_or_venv "${GENERAL_SIM_DIR}" scripts/seed_opensky_live.py \
    --max "${OPENSKY_MAX}" \
    --timeout "${OPENSKY_TIMEOUT}"
fi

log "Done. Open Simulation (Live Flights map mode) after frontend rebuild to see flights."

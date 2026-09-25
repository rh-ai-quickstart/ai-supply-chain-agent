#!/usr/bin/env bash
# Merge supply-chain-network.yaml into gen-sim Postgres + Neo4j via port-forward.
#
# Run after seed-gen-sim-demo.sh (base demo must exist first).
#
# Usage:
#   ./scripts/seed-network-overlay.sh
#   NETWORK_YAML=/path/to/network.yaml make seed-network-overlay
#
# Defaults to data/supply-chain-network.yaml when present; otherwise falls back to
# data/supply-chain-network.example.yaml (copy the example to customize locally).
#
# Overrides:
#   NAMESPACE / GEN_SIM_NAMESPACE  OpenShift project (auto-detected if unset)
#   GENERAL_SIM_DIR                Path to general-simulation checkout
#   NETWORK_YAML                   Overlay YAML path
#   LOCAL_NEO4J_PORT               Default 7687
#   LOCAL_PG_PORT                  Default 5433
#   OC                             oc or kubectl binary (default: oc)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/gen-sim-seed-common.sh
source "${ROOT}/scripts/lib/gen-sim-seed-common.sh"

NETWORK_YAML_DEFAULT="${ROOT}/data/supply-chain-network.yaml"
NETWORK_YAML_EXAMPLE="${ROOT}/data/supply-chain-network.example.yaml"
if [[ -n "${NETWORK_YAML:-}" ]]; then
  :
elif [[ -f "${NETWORK_YAML_DEFAULT}" ]]; then
  NETWORK_YAML="${NETWORK_YAML_DEFAULT}"
elif [[ -f "${NETWORK_YAML_EXAMPLE}" ]]; then
  NETWORK_YAML="${NETWORK_YAML_EXAMPLE}"
  log "Using example overlay ${NETWORK_YAML} (copy to data/supply-chain-network.yaml to customize)"
else
  NETWORK_YAML="${NETWORK_YAML_DEFAULT}"
fi

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

gen_sim_require_cluster "${NS}"
gen_sim_start_port_forwards "${NS}"

export NETWORK_YAML
log "Merging network overlay into Neo4j + Postgres…"
run_with_uv_or_venv "${GENERAL_SIM_DIR}" scripts/seed_network_overlay.py "${NETWORK_YAML}"
log "Done."

#!/usr/bin/env bash
# Merge customer supply-chain network YAML into gen-sim Postgres + Neo4j via port-forward.
#
# Run after `make seed-gen-sim` / seed-gen-sim-demo.sh (base demo must exist first).
#
# Usage:
#   ./scripts/seed-customer-data.sh
#   NETWORK_YAML=/path/to/network.yaml make seed-customer-data
#
# Defaults to data/supply-chain-network.yaml when present; otherwise falls back to
# data/supply-chain-network.example.yaml (copy the example to customize locally).
#
# Overrides:
#   NAMESPACE / GEN_SIM_NAMESPACE  OpenShift project (auto-detected if unset)
#   GENERAL_SIM_DIR                Path to general-simulation checkout
#   NETWORK_YAML                   Customer network YAML path
#   LOCAL_NEO4J_PORT               Default 7687
#   LOCAL_PG_PORT                  Default 5433
#   OC                             oc or kubectl binary (default: oc)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/gen-sim-seed-common.sh
source "${ROOT}/scripts/lib/gen-sim-seed-common.sh"

resolve_network_yaml
gen_sim_prepare_seed scripts/seed_network_overlay.py
log "customer network YAML: ${NETWORK_YAML}"
log "Namespace: ${NS} (SPA reads supply-chain-dashboard — set GEN_SIM_NAMESPACE if wrong)"

export NETWORK_YAML
log "Merging customer network data into Neo4j + Postgres…"
run_with_uv_or_venv "${GENERAL_SIM_DIR}" scripts/seed_network_overlay.py "${NETWORK_YAML}"
log "Done."
log "Refresh Simulation → Live Flights. For the full demo world run: make seed"
log "(seed-gen-sim + OpenSky). Customer YAML alone only seeds entities in the file."

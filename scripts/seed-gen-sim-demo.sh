#!/usr/bin/env bash
# Seed general-simulation Neo4j + Postgres from your laptop via oc port-forward.
#
# Pulls credentials from the cluster, forwards Bolt (7687) and Postgres (local
# 5433 → 5432), then runs general-simulation/scripts/seed_demo.py.
#
# Usage:
#   ./scripts/seed-gen-sim-demo.sh
#   NAMESPACE=general-sim ./scripts/seed-gen-sim-demo.sh
#   make seed-gen-sim
#
# Overrides:
#   NAMESPACE / GEN_SIM_NAMESPACE  OpenShift project (auto-detected if unset)
#   GENERAL_SIM_DIR                Path to general-simulation checkout
#   LOCAL_NEO4J_PORT               Default 7687
#   LOCAL_PG_PORT                  Default 5433 (avoids clashing with local Postgres)
#   OC                             oc or kubectl binary (default: oc)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/gen-sim-seed-common.sh
source "${ROOT}/scripts/lib/gen-sim-seed-common.sh"

need_cmd "${OC}"
need_cmd python3
need_cmd base64

[[ -d "${GENERAL_SIM_DIR}" ]] || fail "general-simulation not found at ${GENERAL_SIM_DIR} (set GENERAL_SIM_DIR)"
[[ -f "${GENERAL_SIM_DIR}/scripts/seed_demo.py" ]] || fail "Missing ${GENERAL_SIM_DIR}/scripts/seed_demo.py"

NS="$(resolve_namespace)"
log "Using namespace: ${NS}"
log "general-simulation: ${GENERAL_SIM_DIR}"
log "Dashboard UI reads general-sim-api in this namespace (supply-chain-dashboard when gen-sim is a subchart; not the separate general-sim project)."

gen_sim_require_cluster "${NS}"
gen_sim_start_port_forwards "${NS}"

log "Seeding Neo4j + Postgres (demo aircraft, maritime, scenarios)…"
run_with_uv_or_venv "${GENERAL_SIM_DIR}" scripts/seed_demo.py
log "Done."

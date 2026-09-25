#!/usr/bin/env bash
# Pull live OpenSky flights on your laptop and upsert into OpenShift Postgres + Neo4j.
#
# OpenSky blocks many AWS/hyperscaler source IPs, so the in-cluster CronJob cannot
# fetch. This script runs the HTTP pull locally, then writes through oc port-forward.
#
# Prefer GEN_SIM_NAMESPACE=supply-chain-dashboard so the dashboard UI sees the data.
#
# Usage:
#   make seed-opensky-live
#   make seed-opensky-live GEN_SIM_NAMESPACE=supply-chain-dashboard OPENSKY_MAX=500
#   ./scripts/seed-opensky-live.sh
#
# Overrides:
#   GEN_SIM_NAMESPACE / NAMESPACE   OpenShift project (auto-detected if unset)
#   GENERAL_SIM_DIR                 Path to general-simulation checkout
#   OPENSKY_MAX                     Max aircraft to upsert (default 2000; 0 = all)
#   OPENSKY_TIMEOUT                 HTTP timeout seconds (default 60)
#   LOCAL_NEO4J_PORT / LOCAL_PG_PORT
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/gen-sim-seed-common.sh
source "${ROOT}/scripts/lib/gen-sim-seed-common.sh"

OPENSKY_MAX="${OPENSKY_MAX:-2000}"
OPENSKY_TIMEOUT="${OPENSKY_TIMEOUT:-60}"

need_cmd "${OC}"
need_cmd python3
need_cmd base64

[[ -d "${GENERAL_SIM_DIR}" ]] || fail "general-simulation not found at ${GENERAL_SIM_DIR} (set GENERAL_SIM_DIR)"
[[ -f "${GENERAL_SIM_DIR}/scripts/seed_opensky_live.py" ]] || fail "Missing ${GENERAL_SIM_DIR}/scripts/seed_opensky_live.py"

NS="$(resolve_namespace)"
log "Using namespace: ${NS}"
log "general-simulation: ${GENERAL_SIM_DIR}"
log "OpenSky max entities: ${OPENSKY_MAX} (0 = unlimited)"
log "Dashboard UI reads general-sim-api / Postgres in this namespace — use supply-chain-dashboard for the SPA."

gen_sim_require_cluster "${NS}"
gen_sim_start_port_forwards "${NS}"

export ENABLED_DOMAINS="${ENABLED_DOMAINS:-aviation}"

log "Fetching OpenSky on this laptop → upserting into cluster Postgres + Neo4j…"
run_with_uv_or_venv "${GENERAL_SIM_DIR}" scripts/seed_opensky_live.py \
  --max "${OPENSKY_MAX}" \
  --timeout "${OPENSKY_TIMEOUT}"
log "Done. Open Simulation (Live Flights map mode) after frontend rebuild to see flights."

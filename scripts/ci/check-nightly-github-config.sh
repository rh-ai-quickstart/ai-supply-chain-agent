#!/usr/bin/env bash
# Verify GitHub Actions secrets/variables required for nightly-dev-testing.yml.
# Does not print secret values.
set -euo pipefail

log() { echo ">>> $*"; }
warn() { echo "WARN: $*" >&2; }

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI is required" >&2
  exit 1
fi

MISSING=0

check_secret() {
  local name="$1"
  if ! gh secret list | awk '{print $1}' | grep -qx "${name}"; then
    warn "Missing repository secret: ${name}"
    MISSING=1
  else
    log "OK secret: ${name}"
  fi
}

check_variable() {
  local name="$1"
  if ! gh variable list | awk '{print $1}' | grep -qx "${name}"; then
    warn "Missing repository variable: ${name}"
    MISSING=1
  else
    log "OK variable: ${name}"
  fi
}

log "Checking nightly workflow prerequisites..."
check_secret PROD_TOKEN
check_secret PROD_SERVER
check_secret LLM_API_TOKEN
check_variable LLM_URL
check_variable LLM_ID

if [ "${MISSING}" -ne 0 ]; then
  echo ""
  echo "Set secrets:  gh secret set PROD_TOKEN"
  echo "              gh secret set PROD_SERVER"
  echo "              gh secret set LLM_API_TOKEN"
  echo "Set variables: gh variable set LLM_URL --body 'https://litemaas.example.com/v1'"
  echo "               gh variable set LLM_ID --body 'Qwen2.5-VL-7B-Instruct'"
  exit 1
fi

log "All nightly prerequisites are configured."

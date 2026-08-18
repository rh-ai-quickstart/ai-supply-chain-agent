#!/usr/bin/env bash
# Read-only checks before local Kind full-stack smoke (Podman VM + Kind node RAM).
# Neo4j's official Helm chart requires 2Gi memory minimum; a 2Gi Podman VM cannot
# schedule it. GHA ubuntu-latest runners have enough RAM — skip this in CI.
set -euo pipefail

USE_PODMAN="${USE_PODMAN:-1}"
MIN_PODMAN_MEMORY_MIB="${MIN_PODMAN_MEMORY_MIB:-8192}"
MIN_KIND_NODE_MIB="${MIN_KIND_NODE_MIB:-3584}"

log() { echo ">>> $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

podman_machine_memory_mib() {
  podman machine inspect --format '{{.Resources.Memory}}' 2>/dev/null | head -1 | tr -d '[:space:]'
}

kind_node_allocatable_mib() {
  if ! command -v kubectl >/dev/null 2>&1; then
    echo 0
    return 0
  fi
  local raw
  raw="$(kubectl get nodes -o jsonpath='{.items[0].status.allocatable.memory}' 2>/dev/null || true)"
  case "${raw}" in
    *Ki) echo $(( ${raw%Ki} / 1024 )) ;;
    *Mi) echo "${raw%Mi}" ;;
    *Gi) echo $(( ${raw%Gi} * 1024 )) ;;
    *) echo 0 ;;
  esac
}

if [[ "${USE_PODMAN}" == "1" ]] && command -v podman >/dev/null 2>&1; then
  mem="$(podman_machine_memory_mib)"
  if [[ -n "${mem}" && "${mem}" =~ ^[0-9]+$ && "${mem}" -lt "${MIN_PODMAN_MEMORY_MIB}" ]]; then
    fail "Podman machine has ${mem} MiB RAM; full-stack Kind needs >= ${MIN_PODMAN_MEMORY_MIB} MiB
(Neo4j requests 2Gi — official chart minimum).

Resize the VM, then recreate the Kind cluster:
  podman machine stop
  podman machine set --memory ${MIN_PODMAN_MEMORY_MIB}
  podman machine start
  make local-kind-smoke-test LOCAL_KIND_SMOKE_ARGS='--recreate --skip-build'"
  fi
  if [[ -n "${mem}" && "${mem}" =~ ^[0-9]+$ ]]; then
    log "Podman machine memory: ${mem} MiB (minimum ${MIN_PODMAN_MEMORY_MIB} MiB)"
  fi
fi

alloc_mib="$(kind_node_allocatable_mib)"
if [[ "${alloc_mib}" =~ ^[0-9]+$ && "${alloc_mib}" -gt 0 && "${alloc_mib}" -lt "${MIN_KIND_NODE_MIB}" ]]; then
  fail "Kind node allocatable memory is ${alloc_mib} MiB; Neo4j's 2Gi request will stay Pending.

After resizing the Podman VM, recreate the cluster so kubelet sees the new RAM:
  make local-kind-smoke-test LOCAL_KIND_SMOKE_ARGS='--recreate --skip-build'"
fi
if [[ "${alloc_mib}" =~ ^[0-9]+$ && "${alloc_mib}" -gt 0 ]]; then
  log "Kind node allocatable memory: ${alloc_mib} MiB (minimum ${MIN_KIND_NODE_MIB} MiB)"
fi

log "Kind preflight passed"

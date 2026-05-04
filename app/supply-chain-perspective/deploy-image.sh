#!/bin/bash

set -euo pipefail

IMAGE="quay.io/robertsandoval/supply-chain-perspective:latest"
CONTAINERFILE="Containerfile-v2"

# API origin baked into the plugin bundle at webpack build time (see Containerfile).
# Leave empty (default) so the browser calls same-origin /api/... and nginx proxies to the
# in-cluster Service (see nginx.conf + Helm values plugin.apiProxy).
# Set only for special cases (e.g. local dev hitting a full URL): env or --api-base-url.
SUPPLY_CHAIN_API_BASE_URL=""
CLI_API_BASE_URL=""

usage() {
  cat <<'EOF'
Usage: deploy-image.sh [OPTIONS]

  (no options)    Build the image and push to the registry.
  --build-only    Build only; do not push.
  --push-only     Push only; do not build (image must already exist locally).

Options:
  -b, --build-only
  -p, --push-only
      --api-base-url URL   Passed to podman as --build-arg SUPPLY_CHAIN_API_BASE_URL=...
                           (overrides SUPPLY_CHAIN_API_BASE_URL env for this run).
  -h, --help      Show this help.

Environment:
  SUPPLY_CHAIN_API_BASE_URL   Same as --api-base-url when the flag is not used.
                              Default empty = same-origin /api/ proxy. Example override: http://localhost:5001

Build:
  podman build --platform linux/amd64 -f Containerfile ...
  Always passes --build-arg SUPPLY_CHAIN_API_BASE_URL=... (from --api-base-url,
  else env SUPPLY_CHAIN_API_BASE_URL, else empty for same-origin /api/... proxy).

EOF
}

do_build=true
do_push=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    -b|--build-only)
      do_push=false
      shift
      ;;
    -p|--push-only)
      do_build=false
      shift
      ;;
    --api-base-url)
      if [[ $# -lt 2 ]]; then
        echo "Error: --api-base-url requires a value." >&2
        exit 1
      fi
      CLI_API_BASE_URL="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$do_build" == false && "$do_push" == false ]]; then
  echo "Error: --build-only and --push-only together do nothing." >&2
  exit 1
fi

if [[ "$do_build" == true ]]; then
  effective_api_base="${CLI_API_BASE_URL:-$SUPPLY_CHAIN_API_BASE_URL}"

  build_cmd=(
    podman build .
    --platform linux/amd64
    -t "$IMAGE"
    -f "$CONTAINERFILE"
    --build-arg "SUPPLY_CHAIN_API_BASE_URL=${effective_api_base}"
  )

  echo "Running: ${build_cmd[*]}"
  "${build_cmd[@]}"
fi

if [[ "$do_push" == true ]]; then
  podman push "$IMAGE"
fi

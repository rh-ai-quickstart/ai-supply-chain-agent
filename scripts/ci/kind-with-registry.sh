#!/bin/sh
# Local Kind cluster + registry mirror (localhost:5001).
# Set USE_PODMAN=1 for Podman (GHA and local). Otherwise uses docker, or podman if docker is absent.
set -o errexit

use_podman() {
  [ "${USE_PODMAN:-0}" = "1" ] || ! command -v docker >/dev/null 2>&1
}

if use_podman; then
  if ! command -v podman >/dev/null 2>&1; then
    echo "podman is required but not installed" >&2
    exit 1
  fi
  echo "Using Podman for Kind and the local registry (KIND_EXPERIMENTAL_PROVIDER=podman)"
  export KIND_EXPERIMENTAL_PROVIDER=podman
  docker() {
    podman "$@"
  }
else
  echo "Using Docker for Kind and the local registry"
fi

reg_name='kind-registry'
reg_port='5001'
if [ "$(docker inspect -f '{{.State.Running}}' "${reg_name}" 2>/dev/null || true)" != 'true' ]; then
  docker run \
    -d --restart=always -p "127.0.0.1:${reg_port}:5000" --network bridge --name "${reg_name}" \
    registry:2
fi

cat <<EOF | kind create cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
containerdConfigPatches:
- |-
  [plugins."io.containerd.grpc.v1.cri".registry]
    config_path = "/etc/containerd/certs.d"
EOF

REGISTRY_DIR="/etc/containerd/certs.d/localhost:${reg_port}"
for node in $(kind get nodes); do
  docker exec "${node}" mkdir -p "${REGISTRY_DIR}"
  cat <<EOF | docker exec -i "${node}" cp /dev/stdin "${REGISTRY_DIR}/hosts.toml"
[host."http://${reg_name}:5000"]
EOF
done

if [ "$(docker inspect -f='{{json .NetworkSettings.Networks.kind}}' "${reg_name}" 2>/dev/null || true)" = 'null' ] || \
   [ "$(docker inspect -f='{{json .NetworkSettings.Networks.kind}}' "${reg_name}" 2>/dev/null || true)" = '' ]; then
  docker network connect kind "${reg_name}" 2>/dev/null || true
fi

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: local-registry-hosting
  namespace: kube-public
data:
  localRegistryHosting.v1: |
    host: "localhost:${reg_port}"
    help: "https://kind.sigs.k8s.io/docs/user/local-registry/"
EOF

echo "Kind cluster ready; push images to localhost:${reg_port}"

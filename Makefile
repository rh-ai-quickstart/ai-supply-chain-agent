# ============================================================
# AI Supply Chain Agent - Build & Deploy Makefile
# ============================================================

# --- Registry & Image Config ---
REGISTRY        ?= quay.io/rh-ee-rjjohnso
BACKEND_IMAGE   ?= $(REGISTRY)/backend
INGEST_IMAGE    ?= $(REGISTRY)/ingestion
FRONTEND_IMAGE  ?= $(REGISTRY)/frontend
BACKEND_TAG     ?= latest
INGEST_TAG      ?= latest
FRONTEND_TAG    ?= latest

# --- Helm Config ---
HELM_CHART     ?= ./helm
HELM_RELEASE   ?= supply-chain-dashboard
NAMESPACE      ?= supply-chain-dashboard
VALUES_FILE    ?= $(HELM_CHART)/values.yaml

# --- Build Args ---
# VITE_API_BASE_URL is set to "" in the Dockerfile; nginx proxies /api/ at runtime.

# --- Podman build platform ---
BUILD_PLATFORM ?= linux/amd64

# ============================================================
# Help
# ============================================================
.PHONY: help
help:
	@echo ""
	@echo "AI Supply Chain Agent - Available Targets"
	@echo "=========================================="
	@echo ""
	@echo "  Build:"
	@echo "    build              Build backend, ingestion, and frontend images"
	@echo "    build-backend      Build the backend (API) container image"
	@echo "    build-ingest       Build the ingestion container image"
	@echo "    build-frontend     Build the frontend container image"
	@echo ""
	@echo "  Push:"
	@echo "    push               Push all images to the registry"
	@echo "    push-backend       Push the backend image"
	@echo "    push-ingest        Push the ingestion image"
	@echo "    push-frontend      Push the frontend image"
	@echo ""
	@echo "  Build & Push:"
	@echo "    release            Build and push all images"
	@echo "    release-backend    Build and push the backend image"
	@echo "    release-ingest     Build and push the ingestion image"
	@echo "    release-frontend   Build and push the frontend image"
	@echo ""
	@echo "  Helm:"
	@echo "    helm-deps          Update Helm chart dependencies"
	@echo "    helm-render        Render chart templates to stdout (dry-run)"
	@echo "    helm-install       Install the Helm release"
	@echo "    helm-upgrade       Upgrade an existing Helm release"
	@echo "    helm-uninstall     Uninstall the Helm release"
	@echo "    helm-status        Show Helm release status"
	@echo ""
	@echo "  Ingest:"
	@echo "    ingest             Run the knowledge-base ingestion Job on OpenShift"
	@echo "    ingest-logs        Tail logs from the most recent ingest Job pod"
	@echo "    ingest-status      Show the status of the ingest Job"
	@echo ""
	@echo "  Utilities:"
	@echo "    login              Log in to the container registry via podman"
	@echo "    oc-status          Show deployed pod and service status"
	@echo "    clean              Remove locally built images"
	@echo ""
	@echo "  Overridable variables (e.g. make build-backend BACKEND_TAG=v2):"
	@echo "    REGISTRY           $(REGISTRY)"
	@echo "    BACKEND_TAG        $(BACKEND_TAG)"
	@echo "    INGEST_TAG         $(INGEST_TAG)"
	@echo "    FRONTEND_TAG       $(FRONTEND_TAG)"
	@echo "    NAMESPACE          $(NAMESPACE)"
	@echo "    HELM_RELEASE       $(HELM_RELEASE)"
	@echo "    (VITE_API_BASE_URL is set to empty in Dockerfile; nginx proxies /api/)"
	@echo ""

# ============================================================
# Build targets
# ============================================================
.PHONY: build
build: build-backend build-ingest build-frontend

.PHONY: build-backend
build-backend:
	@echo ">>> Building backend image: $(BACKEND_IMAGE):$(BACKEND_TAG)"
	podman build \
		--platform $(BUILD_PLATFORM) \
		-t $(BACKEND_IMAGE):$(BACKEND_TAG) \
		./app/backend/api
	@echo ">>> Backend image built successfully."

.PHONY: build-ingest
build-ingest:
	@echo ">>> Building ingestion image: $(INGEST_IMAGE):$(INGEST_TAG)"
	podman build \
		--platform $(BUILD_PLATFORM) \
		-t $(INGEST_IMAGE):$(INGEST_TAG) \
		./app/backend/ingestion
	@echo ">>> Ingestion image built successfully."

.PHONY: build-frontend
build-frontend:
	@echo ">>> Building frontend image: $(FRONTEND_IMAGE):$(FRONTEND_TAG)"
	podman build \
		--platform $(BUILD_PLATFORM) \
		-t $(FRONTEND_IMAGE):$(FRONTEND_TAG) \
		./app/frontend
	@echo ">>> Frontend image built successfully."

# ============================================================
# Push targets
# ============================================================
.PHONY: push
push: push-backend push-ingest push-frontend

.PHONY: push-backend
push-backend:
	@echo ">>> Pushing backend image: $(BACKEND_IMAGE):$(BACKEND_TAG)"
	podman push $(BACKEND_IMAGE):$(BACKEND_TAG)

.PHONY: push-ingest
push-ingest:
	@echo ">>> Pushing ingestion image: $(INGEST_IMAGE):$(INGEST_TAG)"
	podman push $(INGEST_IMAGE):$(INGEST_TAG)

.PHONY: push-frontend
push-frontend:
	@echo ">>> Pushing frontend image: $(FRONTEND_IMAGE):$(FRONTEND_TAG)"
	podman push $(FRONTEND_IMAGE):$(FRONTEND_TAG)

# ============================================================
# Release (build + push) targets
# ============================================================
.PHONY: release
release: release-backend release-ingest release-frontend

.PHONY: release-backend
release-backend: build-backend push-backend

.PHONY: release-ingest
release-ingest: build-ingest push-ingest

.PHONY: release-frontend
release-frontend: build-frontend push-frontend

# ============================================================
# Registry login
# ============================================================
.PHONY: login
login:
	@echo ">>> Logging in to $(REGISTRY)"
	podman login $(shell echo $(REGISTRY) | cut -d'/' -f1)

# ============================================================
# Helm targets
# ============================================================
.PHONY: helm-deps
helm-deps:
	@echo ">>> Updating Helm dependencies in $(HELM_CHART)"
	helm dependency update $(HELM_CHART)

.PHONY: helm-render
helm-render: helm-deps
	@echo ">>> Rendering Helm templates (namespace: $(NAMESPACE))"
	helm template $(HELM_RELEASE) $(HELM_CHART) \
		--namespace $(NAMESPACE) \
		-f $(VALUES_FILE)

.PHONY: helm-install
helm-install: helm-deps
	@echo ">>> Installing Helm release: $(HELM_RELEASE) in namespace: $(NAMESPACE)"
	oc get namespace $(NAMESPACE) 2>/dev/null || oc new-project $(NAMESPACE)
	helm install $(HELM_RELEASE) $(HELM_CHART) \
		--namespace $(NAMESPACE) \
		-f $(VALUES_FILE) \
		--wait \
		--timeout 10m

.PHONY: helm-upgrade
helm-upgrade: helm-deps
	@echo ">>> Upgrading Helm release: $(HELM_RELEASE) in namespace: $(NAMESPACE)"
	helm upgrade $(HELM_RELEASE) $(HELM_CHART) \
		--namespace $(NAMESPACE) \
		-f $(VALUES_FILE) \
		--wait \
		--timeout 10m

.PHONY: helm-uninstall
helm-uninstall:
	@echo ">>> Uninstalling Helm release: $(HELM_RELEASE) from namespace: $(NAMESPACE)"
	helm uninstall $(HELM_RELEASE) --namespace $(NAMESPACE)

.PHONY: helm-status
helm-status:
	helm status $(HELM_RELEASE) --namespace $(NAMESPACE)

# ============================================================
# Utilities
# ============================================================
.PHONY: llamastack-routes
llamastack-routes:
	@echo ">>> Fetching llamastack OpenAPI routes (port-forward must be active)"
	curl -s http://localhost:8321/v1/openapi.json | \
		python3 -c "import sys,json; [print(p) for p in sorted(json.load(sys.stdin)['paths'])]"

.PHONY: llamastack-models
llamastack-models:
	@echo ">>> Listing registered models (port-forward must be active)"
	curl -s http://localhost:8321/v1/models | python3 -m json.tool

.PHONY: llamastack-pf
llamastack-pf:
	@echo ">>> Port-forwarding llamastack :8321 -> localhost:8321 (Ctrl+C to stop)"
	oc port-forward svc/llamastack 8321:8321 -n $(NAMESPACE)

.PHONY: oc-status
oc-status:
	@echo ">>> Pods:"
	oc get pods -n $(NAMESPACE)
	@echo ""
	@echo ">>> Services:"
	oc get svc -n $(NAMESPACE)
	@echo ""
	@echo ">>> InferenceServices:"
	oc get inferenceservice -n $(NAMESPACE) 2>/dev/null || echo "(no InferenceService CRD found)"
	@echo ""
	@echo ">>> Routes:"
	oc get route -n $(NAMESPACE)

# ============================================================
# Ingest targets
# ============================================================

# Run the ingestion Job as a one-off oc run (no Helm required).
# Override INGEST_STRATEGY=llamastack to use the LlamaStack-native pipeline.
INGEST_STRATEGY ?= langchain

.PHONY: ingest
ingest:
	@echo ">>> Running knowledge-base ingestion job in namespace: $(NAMESPACE)"
	oc run ingest-job \
		--image=$(INGEST_IMAGE):$(INGEST_TAG) \
		--restart=Never \
		--rm \
		--attach \
		-n $(NAMESPACE) \
		--command -- python main.py \
		--env INGEST_STRATEGY=$(INGEST_STRATEGY) \
		--env KNOWLEDGE_BASE_DIR=knowledge_base \
		--env INGEST_DROP_OLD=true \
		--env LLAMA_STACK_URL=http://llamastack:8321 \
		--env PG_HOST=pgvector \
		--env PG_PORT=5432 \
		--env PG_USER=postgres \
		--env PG_DB=blueprint

.PHONY: ingest-logs
ingest-logs:
	@echo ">>> Logs for job/$(HELM_RELEASE)-ingest"
	oc logs job/$(HELM_RELEASE)-ingest -n $(NAMESPACE) --all-containers

.PHONY: ingest-status
ingest-status:
	@echo ">>> Ingest Job status:"
	oc get job $(HELM_RELEASE)-ingest -n $(NAMESPACE)
	@echo ""
	@echo ">>> Ingest pods (all phases):"
	oc get pods -n $(NAMESPACE) --selector=job-name=$(HELM_RELEASE)-ingest
	@echo ""
	@echo ">>> Ingest Job events:"
	oc describe job $(HELM_RELEASE)-ingest -n $(NAMESPACE) | tail -20

# ============================================================
# Clean
# ============================================================
.PHONY: clean
clean:
	@echo ">>> Removing local images"
	-podman rmi $(BACKEND_IMAGE):$(BACKEND_TAG) 2>/dev/null
	-podman rmi $(INGEST_IMAGE):$(INGEST_TAG) 2>/dev/null
	-podman rmi $(FRONTEND_IMAGE):$(FRONTEND_TAG) 2>/dev/null
	@echo ">>> Done."

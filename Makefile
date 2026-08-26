# ============================================================
# AI Supply Chain Agent - Build & Deploy Makefile
# ============================================================

# --- Registry & Image Config ---
REGISTRY        ?= quay.io/rh-ai-quickstart
BACKEND_IMAGE      ?= $(REGISTRY)/ai-supply-chain-agent-backend
INGEST_IMAGE       ?= $(REGISTRY)/ai-supply-chain-agent-ingestion
FRONTEND_IMAGE     ?= $(REGISTRY)/ai-supply-chain-agent-frontend
BACKEND_TAG        ?= latest
INGEST_TAG         ?= latest
FRONTEND_TAG       ?= latest
GEN_SIM_TAG        ?= $(BACKEND_TAG)
GEN_SIM_APP_IMAGE  ?= $(REGISTRY)/general-sim-api:$(GEN_SIM_TAG)
GEN_SIM_POSTGRES_IMAGE ?= $(REGISTRY)/general-sim-postgres:$(GEN_SIM_TAG)

# Helm --set flags for container images (supply-chain chart).
HELM_IMAGE_SETS = \
	--set global.registry=$(REGISTRY) \
	--set global.imageTag=$(BACKEND_TAG) \
	--set backend.image.tag=$(BACKEND_TAG) \
	--set frontend.image.tag=$(FRONTEND_TAG) \
	--set ingest.image.tag=$(INGEST_TAG)

# Kind: supply-chain images from local registry via image.repository (avoids
# Helm global.registry bleed into the general-simulation subchart).
HELM_KIND_IMAGE_SETS = \
	--set backend.image.repository=$(REGISTRY)/ai-supply-chain-agent-backend \
	--set backend.image.tag=$(BACKEND_TAG) \
	--set frontend.image.repository=$(REGISTRY)/ai-supply-chain-agent-frontend \
	--set frontend.image.tag=$(FRONTEND_TAG) \
	--set ingest.image.repository=$(REGISTRY)/ai-supply-chain-agent-ingestion \
	--set ingest.image.tag=$(INGEST_TAG)

# --- Helm Config ---
HELM_CHART     ?= ./helm
HELM_RELEASE   ?= supply-chain-dashboard
NAMESPACE      ?= supply-chain-dashboard
VALUES_FILE    ?= $(HELM_CHART)/values.yaml

# --- Podman ---
BUILD_PLATFORM ?= linux/amd64
# Optional on push, e.g. PUSH_EXTRA_ARGS=--tls-verify=false for Kind (localhost:5001)
PUSH_EXTRA_ARGS ?=
# MaaS profile — external-model via helm/values-maas.yaml (see file header).
MAAS_VALUES_FILE ?= $(HELM_CHART)/values-maas.yaml

HELM_EXTRA_ARGS ?=
GENERAL_SIM_CHART_DIR ?= $(CURDIR)/../../general-simulation/deploy/helm/general-simulation

# --- Secrets (auto-applied if helm/secrets.yaml exists) ---
SECRETS_FILE ?= $(HELM_CHART)/secrets.yaml
ifeq ($(wildcard $(SECRETS_FILE)),)
SECRETS_FLAGS =
else
SECRETS_FLAGS = -f $(SECRETS_FILE)
endif

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
	@echo "    build-and-push     Build and push all images (latest tag)"
	@echo "    release            Build and push all images"
	@echo "    release-backend    Build and push the backend image"
	@echo "    release-ingest     Build and push the ingestion image"
	@echo "    release-frontend   Build and push the frontend image"
	@echo ""
	@echo "  Helm:"
	@echo "    helm-deps          Update Helm chart dependencies"
	@echo "    helm-deps-local    Package general-simulation from sibling checkout (before chart is republished to GitHub Pages)"
	@echo "    helm-lint          Lint the Helm chart"
	@echo "    helm-test          Run Helm unit tests (helm-unittest)"
	@echo "    helm-render        Render chart templates to stdout (dry-run)"
	@echo "    helm-install       Install the Helm release (OpenShift project)"
	@echo "    helm-upgrade-install  helm upgrade --install with REGISTRY / secrets"
	@echo "    helm-upgrade-install-maas  MaaS profile (VALUES_FILE=helm/values-maas.yaml)"
	@echo "    helm-upgrade       Upgrade an existing Helm release"
	@echo "    helm-uninstall     Uninstall the Helm release"
	@echo "    helm-status        Show Helm release status"
	@echo "    helm-install-kind  Install on Kind/Kubernetes (values-kind.yaml + local REGISTRY)"
	@echo ""
	@echo "  Test:"
	@echo "    test               Run backend, frontend, and Helm unit tests"
	@echo ""
	@echo "  Lint:"
	@echo "    lint               Run ESLint, ruff, and yamllint on the codebase"
	@echo ""
	@echo "  Quality gate:"
	@echo "    pre-commit         Run lint, test, and helm lint together"
	@echo ""
	@echo "  Kind (CI / local):"
	@echo "    kind-build-images  Build backend, ingest, and frontend for REGISTRY (default localhost:5001)"
	@echo "    kind-push-images   Push kind-build-images to REGISTRY"
	@echo "    k8s-namespace      Create/set kubectl namespace (NAMESPACE)"
	@echo "    kind-verify          Post-deploy checks (port-forward + curl; Kind cluster must be up)"
	@echo "    kind-verify-e2e      kind-verify + Playwright UI tests (RUN_UI_E2E=1)"
	@echo "    kind-preflight       Check Podman VM / Kind node RAM before local smoke"
	@echo "    local-kind-smoke-test  Full local Kind smoke (cluster + images + helm-install-kind + verify)"
	@echo ""
	@echo "  E2E UI (Playwright):"
	@echo "    e2e-ui-install       Install pytest-playwright and Chromium"
	@echo "    e2e-ui               Run browser E2E tests (needs SUPPLY_CHAIN_UI_ENDPOINT)"
	@echo ""
	@echo "  Ingest:"
	@echo "    ingest             Run the knowledge-base ingestion Job on OpenShift"
	@echo "    ingest-logs        Tail logs from the most recent ingest Job pod"
	@echo "    ingest-status      Show the status of the ingest Job"
	@echo ""
	@echo "  Gen-sim demo data:"
	@echo "    seed               Demo seed then live OpenSky (seed-gen-sim + seed-opensky-live)"
	@echo "    seed-gen-sim       Port-forward Neo4j+Postgres, pull secrets, run seed_demo.py"
	@echo "    seed-opensky-live  Pull live OpenSky on laptop → upsert into cluster PG+Neo4j"
	@echo ""
	@echo "  Utilities:"
	@echo "    login              Log in to the container registry via podman"
	@echo "    oc-status          Show deployed pod and service status"
	@echo "    clean              Remove locally built images"
	@echo ""
	@echo "  Overridable variables (e.g. make build-backend BACKEND_TAG=v2):"
	@echo "    GEN_SIM_TAG        $(GEN_SIM_TAG)"
	@echo "    REGISTRY           $(REGISTRY)"
	@echo "    BACKEND_TAG        $(BACKEND_TAG)"
	@echo "    INGEST_TAG         $(INGEST_TAG)"
	@echo "    FRONTEND_TAG       $(FRONTEND_TAG)"
	@echo "    NAMESPACE          $(NAMESPACE)"
	@echo "    GEN_SIM_NAMESPACE  (optional) OpenShift ns with gen-sim postgres+neo4j"
	@echo "    GENERAL_SIM_DIR    $(GENERAL_SIM_DIR)"
	@echo "    OPENSKY_MAX        $(OPENSKY_MAX)  (seed-opensky-live cap; 0=unlimited)"
	@echo "    HELM_RELEASE       $(HELM_RELEASE)"
	@echo "    VALUES_FILE        $(VALUES_FILE)  (set secrets in helm/secrets.yaml — see secrets.example.yaml)"
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
		--build-arg GIT_COMMIT=$$(git rev-parse --short HEAD 2>/dev/null || echo unknown) \
		--build-arg BUILD_TIME=$$(date -u +%Y-%m-%dT%H:%M:%SZ) \
		-f ./app/backend/api/Containerfile \
		-t $(BACKEND_IMAGE):$(BACKEND_TAG) \
		./app/backend/api
	@echo ">>> Backend image built successfully."

.PHONY: build-ingest
build-ingest:
	@echo ">>> Building ingestion image: $(INGEST_IMAGE):$(INGEST_TAG)"
	podman build \
		--platform $(BUILD_PLATFORM) \
		-f ./app/backend/ingestion/Containerfile \
		-t $(INGEST_IMAGE):$(INGEST_TAG) \
		./app/backend/ingestion
	@echo ">>> Ingestion image built successfully."

.PHONY: build-frontend
build-frontend:
	@set -eu; \
	podman build \
		--platform $(BUILD_PLATFORM) \
		--build-arg GIT_COMMIT=$$(git rev-parse --short HEAD 2>/dev/null || echo unknown) \
		--build-arg BUILD_TIME=$$(date -u +%Y-%m-%dT%H:%M:%SZ) \
		-f ./app/frontend/Containerfile \
		-t $(FRONTEND_IMAGE):$(FRONTEND_TAG) \
		./app/frontend; \
	echo ">>> Frontend image built successfully."

# ============================================================
# Push targets
# ============================================================
.PHONY: push
push: push-backend push-ingest push-frontend

.PHONY: push-backend
push-backend:
	@echo ">>> Pushing backend image: $(BACKEND_IMAGE):$(BACKEND_TAG)"
	podman push $(PUSH_EXTRA_ARGS) $(BACKEND_IMAGE):$(BACKEND_TAG)

.PHONY: push-ingest
push-ingest:
	@echo ">>> Pushing ingestion image: $(INGEST_IMAGE):$(INGEST_TAG)"
	podman push $(PUSH_EXTRA_ARGS) $(INGEST_IMAGE):$(INGEST_TAG)

.PHONY: push-frontend
push-frontend:
	@echo ">>> Pushing frontend image: $(FRONTEND_IMAGE):$(FRONTEND_TAG)"
	podman push $(PUSH_EXTRA_ARGS) $(FRONTEND_IMAGE):$(FRONTEND_TAG)

# ============================================================
# Build & Push (all images with latest tag)
# ============================================================
.PHONY: build-and-push
build-and-push: build push

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
# Test targets
# ============================================================

BACKEND_TEST ?= python run_backend_tests.py
FRONTEND_TEST ?= pnpm test
HELM_TEST ?= make helm-test

.PHONY: test
test: test-backend test-frontend test-helm
	@echo ">>> All tests passed."

.PHONY: test-backend
test-backend:
	@echo ">>> Running backend tests..."
	cd app/backend && $(BACKEND_TEST)

.PHONY: test-frontend
test-frontend:
	@echo ">>> Running frontend tests..."
	cd app/frontend && $(FRONTEND_TEST)

.PHONY: test-helm
test-helm: helm-test

# ============================================================
# Lint targets
# ============================================================

.PHONY: lint
lint: lint-backend lint-frontend lint-helm
	@echo ">>> All linters passed."

.PHONY: lint-backend
lint-backend: lint-backend-ruff lint-backend-types

.PHONY: lint-backend-ruff
lint-backend-ruff:
	@echo ">>> Linting Python (ruff)..."
	ruff check app/backend/api app/backend/ingestion

# Scoped to the SOLID-refactored modules (Settings/Container/app_factory,
# repositories, the split LlamaStack clients, routes) — these are the pieces
# with Protocol-based seams where mypy is most valuable today. Widen this list
# as older modules pick up type hints.
MYPY_BACKEND_TARGETS ?= \
	app/backend/api/settings.py \
	app/backend/api/container.py \
	app/backend/api/app_factory.py \
	app/backend/api/main.py \
	app/backend/api/errors.py \
	app/backend/api/clients/chat_completion_client.py \
	app/backend/api/clients/tool_loop_orchestrator.py \
	app/backend/api/clients/llama_vector_store_admin.py \
	app/backend/api/clients/llama_stack_client.py \
	app/backend/api/repositories \
	app/backend/api/services/guardrail_policy.py \
	app/backend/api/services/rag_context_provider.py \
	app/backend/api/services/readiness_service.py \
	app/backend/api/routes

.PHONY: lint-backend-types
lint-backend-types:
	@echo ">>> Type-checking Python (mypy)..."
	cd app/backend && mypy $(patsubst app/backend/%,%,$(MYPY_BACKEND_TARGETS))

.PHONY: lint-frontend
lint-frontend:
	@echo ">>> Linting frontend (ESLint)..."
	cd app/frontend && pnpm run lint

.PHONY: lint-helm
lint-helm:
	@echo ">>> Linting Helm chart..."
	@set -eu; \
	yamllint helm/templates/ 2>/dev/null || echo ">>> (yamllint not installed, skipping)"

# ============================================================
# Helm targets
# ============================================================
.PHONY: helm-deps
helm-deps:
	@echo ">>> Updating Helm dependencies in $(HELM_CHART)"
	helm dependency update $(HELM_CHART)

.PHONY: helm-deps-local
helm-deps-local:
	@echo ">>> Packaging general-simulation from $(GENERAL_SIM_CHART_DIR) into $(HELM_CHART)/charts"
	@test -f "$(GENERAL_SIM_CHART_DIR)/Chart.yaml" || \
	  { echo ">>> ERROR: chart not found. Set GENERAL_SIM_CHART_DIR or clone general-simulation."; exit 1; }
	helm dependency update "$(GENERAL_SIM_CHART_DIR)"
	helm package "$(GENERAL_SIM_CHART_DIR)" -d "$(HELM_CHART)/charts"

.PHONY: helm-lint
helm-lint: helm-deps
	@echo ">>> Linting Helm chart: $(HELM_CHART)"
	helm lint $(HELM_CHART) -f $(VALUES_FILE) $(SECRETS_FLAGS)

.PHONY: helm-test
helm-test: helm-deps
	@echo ">>> Running Helm unit tests: $(HELM_CHART)"
	helm unittest $(HELM_CHART)
	@echo ">>> Validating pgvector Secret password wiring"
	python3 $(HELM_CHART)/tests/test_pgvector_secret.py

.PHONY: helm-render
helm-render: helm-deps
	@echo ">>> Rendering Helm templates (namespace: $(NAMESPACE), registry: $(REGISTRY))"
	@echo ">>> Secrets file: $(if $(SECRETS_FLAGS),$(SECRETS_FILE) (found),not found - see secrets.example.yaml)"
	helm template $(HELM_RELEASE) $(HELM_CHART) \
		--namespace $(NAMESPACE) \
		-f $(VALUES_FILE) \
		$(SECRETS_FLAGS) \
		$(HELM_IMAGE_SETS) \
		$(HELM_EXTRA_ARGS)

.PHONY: helm-install
helm-install: helm-deps
	@echo ">>> Installing Helm release: $(HELM_RELEASE) in namespace: $(NAMESPACE)"
	@echo ">>> Registry: $(REGISTRY) (backend=$(BACKEND_TAG) frontend=$(FRONTEND_TAG) ingest=$(INGEST_TAG))"
	@echo ">>> Secrets file: $(if $(SECRETS_FLAGS),$(SECRETS_FILE) (found),not found - see secrets.example.yaml)"
	oc get namespace $(NAMESPACE) 2>/dev/null || oc new-project $(NAMESPACE)
	helm install $(HELM_RELEASE) $(HELM_CHART) \
		--namespace $(NAMESPACE) \
		-f $(VALUES_FILE) \
		$(SECRETS_FLAGS) \
		$(HELM_IMAGE_SETS) \
		$(HELM_EXTRA_ARGS) \
		--wait \
		--timeout 10m

.PHONY: helm-upgrade
helm-upgrade: helm-deps
	@echo ">>> Upgrading Helm release: $(HELM_RELEASE) in namespace: $(NAMESPACE)"
	@echo ">>> Registry: $(REGISTRY) (backend=$(BACKEND_TAG) frontend=$(FRONTEND_TAG) ingest=$(INGEST_TAG))"
	@echo ">>> Secrets file: $(if $(SECRETS_FLAGS),$(SECRETS_FILE) (found),not found - see secrets.example.yaml)"
	helm upgrade $(HELM_RELEASE) $(HELM_CHART) \
		--namespace $(NAMESPACE) \
		-f $(VALUES_FILE) \
		$(SECRETS_FLAGS) \
		$(HELM_IMAGE_SETS) \
		$(HELM_EXTRA_ARGS) \
		--wait \
		--timeout 10m

.PHONY: helm-upgrade-install
helm-upgrade-install: helm-deps
	@echo ">>> Installing/upgrading Helm release: $(HELM_RELEASE) in namespace: $(NAMESPACE)"
	@echo ">>> Registry: $(REGISTRY) (backend=$(BACKEND_TAG) frontend=$(FRONTEND_TAG) ingest=$(INGEST_TAG))"
	@echo ">>> Secrets file: $(if $(SECRETS_FLAGS),$(SECRETS_FILE) (found),not found - see secrets.example.yaml)"
	helm upgrade --install $(HELM_RELEASE) $(HELM_CHART) \
		--namespace $(NAMESPACE) \
		--create-namespace \
		-f $(VALUES_FILE) \
		$(SECRETS_FLAGS) \
		$(HELM_IMAGE_SETS) \
		$(HELM_EXTRA_ARGS) \
		--wait \
		--timeout 15m

.PHONY: helm-upgrade-install-maas
helm-upgrade-install-maas:
	$(MAKE) helm-upgrade-install VALUES_FILE=$(MAAS_VALUES_FILE)

.PHONY: helm-uninstall
helm-uninstall:
	@echo ">>> Uninstalling Helm release: $(HELM_RELEASE) from namespace: $(NAMESPACE)"
	helm uninstall $(HELM_RELEASE) --namespace $(NAMESPACE)

.PHONY: helm-status
helm-status:
	helm status $(HELM_RELEASE) --namespace $(NAMESPACE)

.PHONY: kind-build-images
kind-build-images: build-backend build-ingest build-frontend

.PHONY: kind-push-images
kind-push-images: push-backend push-ingest push-frontend

.PHONY: k8s-namespace
k8s-namespace:
	@kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	@kubectl config set-context --current --namespace=$(NAMESPACE)

.PHONY: kind-verify
kind-verify:
	@bash ./scripts/ci/kind-verify-deployment.sh

.PHONY: kind-preflight
kind-preflight:
	@bash ./scripts/ci/kind-preflight.sh

.PHONY: kind-verify-e2e
kind-verify-e2e: e2e-ui-install
	@RUN_UI_E2E=1 bash ./scripts/ci/kind-verify-deployment.sh

.PHONY: local-kind-smoke-test
local-kind-smoke-test:
	@bash ./scripts/local-kind-smoke-test.sh $(LOCAL_KIND_SMOKE_ARGS)

.PHONY: e2e-ui-install
e2e-ui-install:
	@echo ">>> Installing Playwright UI test dependencies"
	pip install -r tests/e2e_ui/requirements.txt
	playwright install chromium

.PHONY: e2e-ui
e2e-ui: e2e-ui-install
	@python -m pytest tests/e2e_ui/ -v --tb=short --browser chromium

.PHONY: helm-install-kind
helm-install-kind: helm-deps k8s-namespace
	@echo ">>> Installing $(HELM_RELEASE) on Kind/Kubernetes (namespace: $(NAMESPACE), registry: $(REGISTRY))"
	helm upgrade --install $(HELM_RELEASE) $(HELM_CHART) \
		--namespace $(NAMESPACE) \
		--create-namespace \
		-f $(VALUES_FILE) \
		-f $(KIND_VALUES_FILE) \
		$(SECRETS_FLAGS) \
		$(HELM_KIND_IMAGE_SETS) \
		$(HELM_EXTRA_ARGS) \
		--wait \
		--timeout 15m

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
	@oc get route -n $(NAMESPACE) -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{"https://"}{.spec.host}{"\n"}{end}'

# ============================================================
# Ingest targets
# ============================================================

# Run the ingestion Job as a one-off oc run (no Helm required).
# Default matches helm/values.yaml ingest.strategy; override to langchain for PGVector.
INGEST_STRATEGY ?= llamastack

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
		--env PG_HOST=postgres \
		--env PG_PORT=5432 \
		--env PG_USER=sim \
		--env PG_DB=sim

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
# Gen-sim demo seed (laptop → OpenShift Neo4j + Postgres)
# ============================================================
# Requires a local checkout of general-simulation (sibling by default) and oc
# login. Pulls neo4j-auth + postgres-credentials from the cluster.
GENERAL_SIM_DIR ?= $(CURDIR)/../general-simulation
GEN_SIM_NAMESPACE ?=
OPENSKY_MAX ?= 2000

.PHONY: seed-gen-sim
seed-gen-sim:
	@echo ">>> Seeding gen-sim demo data from laptop (port-forward + cluster secrets)"
	NAMESPACE=$(NAMESPACE) \
	GEN_SIM_NAMESPACE=$(GEN_SIM_NAMESPACE) \
	GENERAL_SIM_DIR=$(GENERAL_SIM_DIR) \
	./scripts/seed-gen-sim-demo.sh

.PHONY: seed-opensky-live
seed-opensky-live:
	@echo ">>> Pulling live OpenSky on laptop → cluster Postgres + Neo4j"
	NAMESPACE=$(NAMESPACE) \
	GEN_SIM_NAMESPACE=$(GEN_SIM_NAMESPACE) \
	GENERAL_SIM_DIR=$(GENERAL_SIM_DIR) \
	OPENSKY_MAX=$(OPENSKY_MAX) \
	./scripts/seed-opensky-live.sh

.PHONY: seed
seed: seed-gen-sim seed-opensky-live
	@echo ">>> seed complete (demo scenarios/maritime + live OpenSky flights)"

# ============================================================
# Quality gate
# ============================================================

.PHONY: pre-commit
pre-commit: lint test
	@echo ">>> Pre-commit checks completed."

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


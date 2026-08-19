#!/usr/bin/env python3
"""Guardrails for the shared Postgres Helm Secret password (Secret/pgvector).

general-simulation 0.0.1 creates Secret/pgvector for Llama Stack (see
``llamastack-pg-secret.yaml`` in the gen-sim chart). The secrets overlay must
never blank ``general-simulation.postgres.postgres.password``. An empty string
replaces the chart default and produces a Secret with no password, which makes
LlamaStack crash with::

    FATAL: password authentication failed for user "sim"

Keep ``general-simulation.postgres.postgres.password`` in sync with every
``general-simulation.*.postgres.password`` block. Postgres only applies
``POSTGRES_PASSWORD`` on first init, so changing the password after install
also requires deleting the gen-sim Postgres PVC.
"""

from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
HELM_CHART = REPO_ROOT / "helm"
VALUES = HELM_CHART / "values.yaml"
VALUES_KIND = HELM_CHART / "values-kind.yaml"
SECRETS_EXAMPLE = HELM_CHART / "secrets.example.yaml"

# Neo4j subchart does live-cluster lookups unless disabled — not needed for
# Secret/pgvector guardrails.
_HELM_TEMPLATE_SETS = [
    "general-simulation.neo4j.disableLookups=true",
    "general-simulation.neo4j.neo4j.password=demo-password",
    "general-simulation.api.neo4j.password=demo-password",
    "general-simulation.bootstrap.neo4j.password=demo-password",
    "general-simulation.ingestion.neo4j.password=demo-password",
]


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise AssertionError(f"{path} must parse to a mapping, got {type(data)}")
    return data


def _postgres_password_from_values(data: dict) -> str | None:
    postgres = (data.get("general-simulation") or {}).get("postgres") or {}
    pg = postgres.get("postgres") or {}
    if "password" not in pg:
        return None
    value = pg.get("password")
    if value is None:
        return None
    return str(value)


def _helm_template(*value_files: Path, extra_sets: list[str] | None = None) -> str:
    cmd = [
        "helm",
        "template",
        "pgvector-password-check",
        str(HELM_CHART),
        "--namespace",
        "supply-chain-dashboard",
    ]
    for flag in _HELM_TEMPLATE_SETS:
        cmd.extend(["--set", flag])
    if extra_sets:
        for flag in extra_sets:
            cmd.extend(["--set", flag])
    for path in value_files:
        cmd.extend(["-f", str(path)])
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def _collect_gen_sim_images(manifest: str) -> list[str]:
    images: list[str] = []
    for doc in yaml.safe_load_all(manifest):
        if not isinstance(doc, dict):
            continue
        if doc.get("kind") not in ("Deployment", "StatefulSet", "Job"):
            continue
        spec = doc.get("spec") or {}
        pod = (spec.get("template") or {}).get("spec") or {}
        for container in (pod.get("initContainers") or []) + (pod.get("containers") or []):
            image = container.get("image") or ""
            if "general-sim-" in image:
                images.append(image)
    return images


def _kind_values_have_no_per_image_pins() -> None:
    """values-kind.yaml must rely on general-simulation.global.registry, not full image URLs."""
    data = _load_yaml(VALUES_KIND)
    gen_sim = data.get("general-simulation") or {}
    for key in ("postgres", "api", "bootstrap"):
        block = gen_sim.get(key) or {}
        assert "image" not in block, (
            f"values-kind.yaml general-simulation.{key}.image must not be set — "
            "use general-simulation.global.registry instead"
        )


def _rendered_pgvector_secret_fields(manifest: str) -> dict[str, str]:
    docs = list(yaml.safe_load_all(manifest))
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        if doc.get("kind") != "Secret":
            continue
        if (doc.get("metadata") or {}).get("name") != "pgvector":
            continue
        data = doc.get("data") or {}
        string_data = doc.get("stringData") or {}
        decoded: dict[str, str] = {}
        for key, raw in data.items():
            if raw in (None, ""):
                decoded[key] = ""
            else:
                decoded[key] = base64.b64decode(raw).decode("utf-8")
        for key, value in string_data.items():
            decoded[key] = str(value)
        return decoded
    raise AssertionError("Rendered manifests do not include Secret/pgvector")


def test_secrets_example_does_not_blank_postgres_password() -> None:
    """Comment-only postgres blocks must not wipe chart defaults."""
    example = _load_yaml(SECRETS_EXAMPLE)
    gen_sim = example.get("general-simulation")
    if gen_sim is None:
        return
    assert isinstance(gen_sim, dict), (
        f"{SECRETS_EXAMPLE.relative_to(REPO_ROOT)}: general-simulation must be "
        "a mapping when present (not null)"
    )
    postgres = gen_sim.get("postgres")
    if postgres is None:
        return
    assert isinstance(postgres, dict), (
        f"{SECRETS_EXAMPLE.relative_to(REPO_ROOT)}: general-simulation.postgres "
        "must be a mapping when present"
    )
    pg = postgres.get("postgres")
    if pg is None:
        return
    assert isinstance(pg, dict), (
        f"{SECRETS_EXAMPLE.relative_to(REPO_ROOT)}: "
        "general-simulation.postgres.postgres must be a mapping with keys"
    )
    if "password" in pg:
        assert pg.get("password") not in (None, ""), (
            f"{SECRETS_EXAMPLE.relative_to(REPO_ROOT)} must not set "
            "general-simulation.postgres.postgres.password to an empty string"
        )


def test_committed_values_define_non_empty_password() -> None:
    data = _load_yaml(VALUES)
    password = _postgres_password_from_values(data)
    assert password, (
        f"{VALUES.relative_to(REPO_ROOT)} must define a non-empty "
        "general-simulation.postgres.postgres.password demo default"
    )


def test_helm_render_keeps_non_empty_password_with_secrets_example() -> None:
    """values.yaml + secrets.example.yaml must still render a usable password."""
    manifest = _helm_template(VALUES, SECRETS_EXAMPLE)
    fields = _rendered_pgvector_secret_fields(manifest)
    assert fields.get("password"), (
        "Rendered Secret/pgvector.password is empty when applying "
        "secrets.example.yaml over values.yaml — LlamaStack cannot auth to Postgres"
    )


def test_helm_render_values_alone_has_password() -> None:
    manifest = _helm_template(VALUES)
    fields = _rendered_pgvector_secret_fields(manifest)
    assert fields.get("password"), (
        "Rendered Secret/pgvector.password is empty for values.yaml alone"
    )


def test_gen_sim_pgvector_secret_points_at_postgres() -> None:
    """Llama Stack Secret must target gen-sim Postgres Service sim/sim."""
    manifest = _helm_template(VALUES)
    fields = _rendered_pgvector_secret_fields(manifest)
    assert fields.get("host") == "postgres"
    assert fields.get("user") == "sim"
    assert fields.get("dbname") == "sim"


def _rendered_neo4j_auth_password(manifest: str) -> str:
    docs = list(yaml.safe_load_all(manifest))
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        if doc.get("kind") != "Secret":
            continue
        if (doc.get("metadata") or {}).get("name") != "neo4j-auth":
            continue
        string_data = doc.get("stringData") or {}
        if "NEO4J_AUTH" in string_data:
            return str(string_data["NEO4J_AUTH"])
        data = doc.get("data") or {}
        raw = data.get("NEO4J_AUTH")
        if raw:
            return base64.b64decode(raw).decode("utf-8")
    raise AssertionError("Rendered manifests do not include Secret/neo4j-auth")


def test_helm_render_creates_neo4j_auth_secret() -> None:
    """gen-sim 0.0.1 umbrella must create neo4j-auth for the official neo4j chart."""
    manifest = _helm_template(VALUES)
    auth = _rendered_neo4j_auth_password(manifest)
    assert auth.startswith("neo4j/"), (
        "Secret/neo4j-auth.NEO4J_AUTH must use neo4j/<password> format"
    )
    assert len(auth) > len("neo4j/"), (
        "Secret/neo4j-auth is empty — neo4j StatefulSet cannot start"
    )


def test_helm_render_creates_neo4j_service_account() -> None:
    manifest = _helm_template(VALUES)
    docs = list(yaml.safe_load_all(manifest))
    names = {
        (doc.get("metadata") or {}).get("name")
        for doc in docs
        if isinstance(doc, dict) and doc.get("kind") == "ServiceAccount"
    }
    assert "neo4j-sa" in names, (
        "general-simulation must render ServiceAccount/neo4j-sa for OpenShift anyuid"
    )


def test_kind_overlay_does_not_require_pgvector_or_neo4j_sa() -> None:
    """Kind disables llama-stack (no Secret/pgvector) and Neo4j SCC (no neo4j-sa)."""
    _kind_values_have_no_per_image_pins()
    # Simulate helm-install-kind: local supply-chain repos, gen-sim from values-kind global.registry.
    kind_sets = [
        "backend.image.repository=localhost:5001/ai-supply-chain-agent-backend",
        "backend.image.tag=latest",
        "frontend.image.repository=localhost:5001/ai-supply-chain-agent-frontend",
        "frontend.image.tag=latest",
    ]
    manifest = _helm_template(VALUES, VALUES_KIND, extra_sets=kind_sets)
    docs = [doc for doc in yaml.safe_load_all(manifest) if isinstance(doc, dict)]

    sa_names = {
        (doc.get("metadata") or {}).get("name")
        for doc in docs
        if doc.get("kind") == "ServiceAccount"
    }
    assert "neo4j-sa" not in sa_names, (
        "values-kind.yaml disables OpenShift SCC — neo4j must not require neo4j-sa"
    )

    neo4j_sa = None
    backend_secret = None
    gen_sim_images = _collect_gen_sim_images(manifest)
    for doc in docs:
        kind = doc.get("kind")
        name = (doc.get("metadata") or {}).get("name")
        if kind == "StatefulSet" and name == "neo4j":
            neo4j_sa = doc["spec"]["template"]["spec"].get("serviceAccountName")
        if kind == "Deployment" and str(name).endswith("-backend"):
            for env in doc["spec"]["template"]["spec"]["containers"][0].get("env") or []:
                if env.get("name") == "PG_PASSWORD":
                    backend_secret = ((env.get("valueFrom") or {}).get("secretKeyRef") or {}).get(
                        "name"
                    )

    assert neo4j_sa == "default", (
        f"Kind Neo4j StatefulSet must use ServiceAccount default, got {neo4j_sa!r}"
    )
    assert backend_secret == "postgres-credentials", (
        "Kind backend must read PG_PASSWORD from postgres-credentials when llama-stack is off"
    )
    assert gen_sim_images, "Kind overlay must render general-sim platform images"
    assert all(image.startswith("quay.io/") for image in gen_sim_images), (
        f"gen-sim images must use quay.io registry (not localhost:5001): {gen_sim_images}"
    )
    assert not any("localhost:5001" in image for image in gen_sim_images), (
        f"gen-sim images must not be rewritten to local registry: {gen_sim_images}"
    )


def test_rendered_secret_pgvector_is_not_duplicated_with_gen_sim_enabled() -> None:
    """general-simulation 0.2.0 bundles its own llama-stack + pgvector Secret.

    If the subchart's bundled llama-stack is left enabled it renders a second
    Secret/pgvector (llamastack-pg-secret.yaml), and `helm install` fails with
    ``secrets "pgvector" already exists``. values.yaml must disable it so the
    umbrella bridge Secret is the only Secret/pgvector.
    """
    cmd = [
        "helm",
        "template",
        "duplicate-pgvector-check",
        str(HELM_CHART),
        "--namespace",
        "supply-chain-dashboard",
        # Disable lookups/required secrets that need a live cluster or the
        # secrets overlay; the pgvector Secret collision is independent of them.
        "--set",
        "general-simulation.neo4j.disableLookups=true",
        "--set",
        "llm-service.secret.hf_token=unused",
        "--set",
        "general-simulation.api.llm.apiKey=unused",
        "--set",
        "general-simulation.api.postgres.password=demo",
        "--set",
        "general-simulation.api.neo4j.password=demo",
        "--set",
        "general-simulation.bootstrap.postgres.password=demo",
        "--set",
        "general-simulation.bootstrap.neo4j.password=demo",
        "--set",
        "general-simulation.postgres.postgres.password=demo",
        "-f",
        str(VALUES),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    secrets = []
    for doc in yaml.safe_load_all(result.stdout):
        if not isinstance(doc, dict):
            continue
        if doc.get("kind") != "Secret":
            continue
        if (doc.get("metadata") or {}).get("name") == "pgvector":
            secrets.append((doc.get("metadata") or {}).get("name"))
    assert len(secrets) == 1, (
        "Expected exactly one Secret/pgvector with the subchart enabled, "
        f"got {len(secrets)}. Disable general-simulation.llama-stack (and its "
        "pgvector) in values.yaml so the umbrella bridge Secret is the only one."
    )


def main() -> int:
    tests = [
        test_secrets_example_does_not_blank_postgres_password,
        test_committed_values_define_non_empty_password,
        test_helm_render_values_alone_has_password,
        test_helm_render_keeps_non_empty_password_with_secrets_example,
        test_gen_sim_pgvector_secret_points_at_postgres,
        test_helm_render_creates_neo4j_auth_secret,
        test_helm_render_creates_neo4j_service_account,
        test_kind_overlay_does_not_require_pgvector_or_neo4j_sa,
    ]
    failed = 0
    for test in tests:
        try:
            test()
        except subprocess.CalledProcessError as exc:
            failed += 1
            sys.stderr.write(
                f"FAIL {test.__name__}: helm exited {exc.returncode}\n"
                f"{exc.stderr}\n"
            )
        except Exception as exc:  # noqa: BLE001 - surface assertion text to CI
            failed += 1
            sys.stderr.write(f"FAIL {test.__name__}: {exc}\n")
        else:
            print(f"PASS {test.__name__}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

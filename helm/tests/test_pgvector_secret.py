#!/usr/bin/env python3
"""Guardrails for the shared Postgres Helm Secret password (Secret/pgvector).

With ``pgvector.enabled: false`` (default), the umbrella bridge template
creates Secret/pgvector for Llama Stack. The secrets overlay must never blank
``pgvector.secret.password``. An empty string replaces the chart default and
produces a Secret with no password, which makes LlamaStack crash with::

    FATAL: password authentication failed for user "sim"

Keep ``pgvector.secret.password`` in sync with
``general-simulation.postgres.postgres.password``. Postgres only applies
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
SECRETS_EXAMPLE = HELM_CHART / "secrets.example.yaml"


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise AssertionError(f"{path} must parse to a mapping, got {type(data)}")
    return data


def _pgvector_password_from_values(data: dict) -> str | None:
    secret = (data.get("pgvector") or {}).get("secret") or {}
    if "password" not in secret:
        return None
    value = secret.get("password")
    if value is None:
        return None
    return str(value)


def _helm_template(*value_files: Path) -> str:
    cmd = [
        "helm",
        "template",
        "pgvector-password-check",
        str(HELM_CHART),
        "--namespace",
        "supply-chain-dashboard",
        # This guardrail only cares about Secret/pgvector. general-simulation
        # is an unrelated, independently-toggled subchart with its own required
        # Neo4j lookup that `helm template` can never satisfy without a real
        # cluster — disable it so this check stays scoped to the bridge Secret.
        "--set",
        "general-simulation.enabled=false",
    ]
    for path in value_files:
        cmd.extend(["-f", str(path)])
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def _rendered_pgvector_password(manifest: str) -> str:
    docs = list(yaml.safe_load_all(manifest))
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        if doc.get("kind") != "Secret":
            continue
        if (doc.get("metadata") or {}).get("name") != "pgvector":
            continue
        data = doc.get("data") or {}
        raw = data.get("password")
        if raw in (None, ""):
            return ""
        return base64.b64decode(raw).decode("utf-8")
    raise AssertionError("Rendered manifests do not include Secret/pgvector")


def test_secrets_example_does_not_blank_password() -> None:
    """``password: ""`` or a null ``pgvector.secret`` would wipe chart defaults."""
    example = _load_yaml(SECRETS_EXAMPLE)
    pgvector = example.get("pgvector")
    if pgvector is None:
        return
    assert isinstance(pgvector, dict), (
        f"{SECRETS_EXAMPLE.relative_to(REPO_ROOT)}: pgvector must be a mapping "
        "when present (not null)"
    )
    if "secret" not in pgvector:
        return
    secret = pgvector.get("secret")
    assert isinstance(secret, dict), (
        f"{SECRETS_EXAMPLE.relative_to(REPO_ROOT)}: pgvector.secret must be a "
        "mapping with keys — a comment-only block is YAML null and wipes "
        "user/host/dbname/password from values.yaml"
    )
    if "password" in secret:
        assert secret.get("password") not in (None, ""), (
            f"{SECRETS_EXAMPLE.relative_to(REPO_ROOT)} must not set "
            "pgvector.secret.password to an empty string; omit the key or set a "
            "non-empty override"
        )


def test_committed_values_define_non_empty_password() -> None:
    data = _load_yaml(VALUES)
    password = _pgvector_password_from_values(data)
    assert password, (
        f"{VALUES.relative_to(REPO_ROOT)} must define a non-empty "
        "pgvector.secret.password demo default"
    )


def test_helm_render_keeps_non_empty_password_with_secrets_example() -> None:
    """values.yaml + secrets.example.yaml must still render a usable password."""
    manifest = _helm_template(VALUES, SECRETS_EXAMPLE)
    password = _rendered_pgvector_password(manifest)
    assert password, (
        "Rendered Secret/pgvector.password is empty when applying "
        "secrets.example.yaml over values.yaml — LlamaStack cannot auth to Postgres"
    )


def test_helm_render_values_alone_has_password() -> None:
    manifest = _helm_template(VALUES)
    password = _rendered_pgvector_password(manifest)
    assert password, "Rendered Secret/pgvector.password is empty for values.yaml alone"


def test_bridge_secret_points_at_shared_postgres() -> None:
    """Default shared-DB mode must target Service postgres / db sim."""
    data = _load_yaml(VALUES)
    pg = data.get("pgvector") or {}
    assert pg.get("enabled") is False, "default install should disable pgvector STS"
    secret = pg.get("secret") or {}
    assert secret.get("host") == "postgres"
    assert secret.get("user") == "sim"
    assert secret.get("dbname") == "sim"


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
        test_secrets_example_does_not_blank_password,
        test_committed_values_define_non_empty_password,
        test_helm_render_values_alone_has_password,
        test_helm_render_keeps_non_empty_password_with_secrets_example,
        test_bridge_secret_points_at_shared_postgres,
        test_rendered_secret_pgvector_is_not_duplicated_with_gen_sim_enabled,
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

"""Download evaluation artifacts from MLflow by run name."""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path

import mlflow
from mlflow import MlflowClient

LOGGER = logging.getLogger("supply_chain_disruption_eval")
DEFAULT_DOWNLOAD_DIR = Path("/tmp/supply-chain-agent-eval-artifacts")


class ArtifactDownloadError(RuntimeError):
    """An evaluation run or its artifacts could not be downloaded."""


def _escape_filter_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _find_run(client: MlflowClient, run_name: str):
    experiments = client.search_experiments()
    if not experiments:
        raise ArtifactDownloadError(
            "No MLflow experiments are visible in this workspace."
        )

    escaped_name = _escape_filter_value(run_name)
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id for experiment in experiments],
        filter_string=f"tags.mlflow.runName = '{escaped_name}'",
        order_by=["attributes.start_time DESC"],
        max_results=1000,
    )
    exact_matches = [run for run in runs if run.info.run_name == run_name]
    if not exact_matches:
        raise ArtifactDownloadError(
            f"No MLflow run named {run_name!r} was found in the current workspace. "
            "Check the run name and MLflow workspace."
        )
    if len(exact_matches) > 1:
        LOGGER.warning(
            "Found %d runs named %r; downloading the most recent one (%s)",
            len(exact_matches),
            run_name,
            exact_matches[0].info.run_id,
        )
    return exact_matches[0]


def _destination_for_run(download_root: Path, run_name: str, run_id: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", run_name).strip("._") or "evaluation"
    return download_root / f"{safe_name}-{run_id[:8]}"


def download_evaluation_artifacts(run_name: str, download_root: Path) -> Path:
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "").strip()
    if not tracking_uri.startswith(("https://", "http://")):
        raise ArtifactDownloadError(
            "Set MLFLOW_TRACKING_URI to the OpenShift AI MLflow endpoint."
        )

    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()
    run = _find_run(client, run_name)
    run_id = run.info.run_id

    artifacts = client.list_artifacts(run_id, "evaluation")
    if not artifacts:
        raise ArtifactDownloadError(
            f"Run {run_name!r} ({run_id}) has no artifacts under evaluation/. "
            "Check the run's evaluation.artifact_upload_status tag."
        )

    destination = _destination_for_run(download_root, run_name, run_id)
    destination.mkdir(parents=True, exist_ok=True)
    local_path = client.download_artifacts(run_id, "evaluation", str(destination))
    return Path(local_path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "run_name",
        nargs="?",
        default=os.getenv("EVAL_RUN_NAME"),
        help="Exact MLflow run name; defaults to EVAL_RUN_NAME.",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path(os.getenv("EVAL_DOWNLOAD_DIR", str(DEFAULT_DOWNLOAD_DIR))),
        help="Directory under which the run's artifacts are downloaded.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=os.getenv("EVAL_LOG_LEVEL", "INFO"))
    args = _parse_args()
    run_name = (args.run_name or "").strip()
    if not run_name:
        LOGGER.error("Pass an MLflow run name or set EVAL_RUN_NAME.")
        return 2

    try:
        local_path = download_evaluation_artifacts(run_name, args.download_dir)
    except ArtifactDownloadError as exc:
        LOGGER.error("%s", exc)
        return 2
    except Exception:
        LOGGER.exception("Could not download artifacts for MLflow run %r", run_name)
        return 2

    print(f"Downloaded evaluation artifacts to: {local_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

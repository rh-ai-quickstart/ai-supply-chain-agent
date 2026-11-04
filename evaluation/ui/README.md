# Disruption UI evaluation

This scenario evaluation harness is separate from `tests/e2e_ui/`. It uses
Playwright to drive the deployed dashboard, then reads the backend's MLflow
chat traces and scores the question and answer recorded there. Run it from an
OpenShift AI Workbench console with `make run-eval`; there is no evaluator Job
or evaluator container image to build.

## Prerequisites

- OpenShift AI and its MLflow Operator are installed and the namespace has an
  MLflow tracking endpoint.
- The backend deployment can reach that endpoint and has MLflow's
  `mlflow-operator-mlflow-integration` role bound to its service account in
  the application namespace. The Helm chart creates this namespace-scoped
  RoleBinding when backend tracing is enabled.
- The Workbench can reach the frontend route and the disruption knowledge base
  is available.
- A judge model endpoint and its provider credential are available to the
  Workbench.

MLflow stores experiment metadata in its configured backend and trace/artifact
data in the platform's configured artifact store. The Workbench and backend
need tracking access; neither needs namespace-admin privileges for MLflow.
Namespace admin can configure the application and namespace RoleBinding when
the operator-provided ClusterRole is present and bindable.

## Enable backend tracing

Tracing is off by default. Set `ENABLE_EVALS=true` and the OpenShift AI MLflow
route in the deployment shell, then deploy or upgrade through Make:

```bash
export ENABLE_EVALS=true
export MLFLOW_TRACKING_URI="https://<openshift-ai-mlflow-route>"
make helm-upgrade-install
```

For an existing release, `make helm-upgrade` applies the same settings. Make
maps `ENABLE_EVALS` to `backend.tracing.enabled` and `MLFLOW_TRACKING_URI` to
`backend.tracing.trackingUri`. The chart sets the backend tracing and
Kubernetes-namespaced MLflow authentication environment variables and creates
the namespace-scoped RoleBinding. When `ENABLE_EVALS` is unset, the chart's
configured tracing values are left unchanged. The default experiment is
`supply-chain-disruption-evals`; change it only if you also configure the
evaluator to use the same experiment.

The backend pods restart and write a startup trace containing a unique process
session ID and start time. `make run-eval` uses the newest startup marker to
confirm the active backend process, then reads model traces created during that
evaluation invocation. This implementation expects one backend replica so the
startup marker identifies the process handling the evaluation.

MLflow's OpenAI autologging automatically captures model prompts, completions,
latency, token use, model metadata, and function-call responses—including
streamed calls. The backend also records an `agent.chat` chain span around each
model-backed chat request and a `RETRIEVER` span for each knowledge-base search.
The retriever span records the search query, selected vector-store ID, and
retrieved text in MLflow's expected chunk format. OpenAI autologging records
the model calls inside the chat trace; the startup marker identifies the
backend restart boundary. Other tool execution is not separately instrumented.

While enabled, the backend records **all model calls made for chat requests it
handles**, not only the curated evaluation questions. Traces can contain user
prompts, chat history, model responses, and requested function calls. A later
model prompt may include a tool result, but only knowledge-base retrieval is
recorded as a dedicated tool span. Chat paths that return
without calling a model, such as a guardrail shortcut, do not create an
autolog trace.
Use a dedicated evaluation deployment or run in a quiet evaluation window; turn
tracing off for deployments handling ordinary conversations. When disabled,
the backend does not send OpenAI model traces to MLflow.

## Install and configure the Workbench runner

```bash
make eval-ui-install
```

This installs pinned Python packages in a local virtual environment and
downloads Chromium under the same directory. The runner defaults to Python
3.13 because the pinned Playwright dependency chain's `greenlet` version can
fail to build against Python 3.14. `make run-eval` performs setup on its first
invocation. Choose another installed version with
`EVAL_UI_PYTHON_VERSION=3.12`. If Python 3.13 is installed at a nonstandard
path, set `EVAL_UI_BASE_PYTHON=/path/to/python3.13`. The Workbench image needs
the system libraries required by Chromium.

The OpenShift AI Workbench integration normally injects `MLFLOW_TRACKING_URI`.
`make run-eval` sets `MLFLOW_TRACKING_AUTH=kubernetes-namespaced`. When `oc` is
available and logged in, Make supplies `oc whoami --show-token` as
`MLFLOW_TRACKING_TOKEN` and `oc project -q` as `MLFLOW_WORKSPACE`; explicitly
set values take precedence. Without an `oc` token, MLflow can use the
Workbench service-account token or kubeconfig credentials. For a local run,
log in with `oc login` and select a namespace that has access to the MLflow
workspace. `make run-eval` also discovers the frontend Route named
`<HELM_RELEASE>-frontend` in
`NAMESPACE` using `oc` and uses its HTTPS URL. The defaults are
`HELM_RELEASE=supply-chain-dashboard` and `NAMESPACE=supply-chain-dashboard`.
You can override either value, or set `EVAL_UI_URL` explicitly. For a
MaaS-hosted judge, configure its base URL, model ID, and API token:

```bash
export EVAL_JUDGE_MODEL_URL="https://maas-rhdp.apps.maas.redhatworkshops.io/v1"
export EVAL_JUDGE_MODEL_ID="qwen38-27b"
# Set EVAL_JUDGE_API_KEY to the MaaS API token through a secret-backed Workbench variable.
make run-eval
```

Use the MaaS API to find the model ID available to your token:

```bash
curl "$EVAL_JUDGE_MODEL_URL/models" \
  -H "Authorization: Bearer $EVAL_JUDGE_API_KEY"
```

`run-eval` formats the MaaS model ID as `openai:/<MaaS-model-id>` for custom
MLflow judges and passes `EVAL_JUDGE_MODEL_URL` directly to them. The evaluator
adds `/chat/completions` to the configured `/v1` API base.

The evaluator also runs MLflow's built-in `RelevanceToQuery`, `Safety`,
`RetrievalSufficiency`, `RetrievalRelevance`, and `RetrievalGroundedness`
judges as `builtin_relevance_to_query`, `builtin_safety`,
`builtin_retrieval_sufficiency`, `builtin_retrieval_relevance`, and
`builtin_retrieval_groundedness`. They use the
configured MaaS model ID, endpoint, and API key. The built-in classes in pinned
MLflow 3.13 don't expose `base_url` consistently; the runner routes their shared
judge calls to the configured chat URL instead of public OpenAI. The adapter is
specific to the pinned MLflow version and should be rechecked when upgrading.

The runner allows 180 seconds per judge request and limits evaluation and scorer
workers to one each by default, so only one judge request is in flight at a time.
Override these with
`EVAL_JUDGE_TIMEOUT_SECONDS` and `EVAL_JUDGE_MAX_CONCURRENT_SCORERS` when
calling `make run-eval`. If a judge still fails with a transient connection
drop or timeout after MLflow's own retries, the scorer makes up to three
additional attempts after 10, 30, and 120 seconds. Set
`EVAL_JUDGE_TRANSIENT_RETRIES` (0–3, default 3) to change the number of
additional attempts.

For a deployment in another namespace or Helm release:

```bash
make run-eval NAMESPACE=<application-namespace> HELM_RELEASE=<release-name>
```

`run-eval` maps `EVAL_JUDGE_API_KEY` to `OPENAI_API_KEY` for the judge request.
These settings are separate from `MLFLOW_TRACKING_URI`: the MaaS URL is the
judge inference endpoint, while the tracking URI is the OpenShift AI MLflow
server. The Kubernetes credentials used for MLflow do not authenticate to
MaaS. The runner refuses to use a local
MLflow file store if the tracking URI is missing. The evaluator's
`EVAL_MLFLOW_EXPERIMENT` must match the backend's
`backend.tracing.experiment` value so it can find the runtime traces.

To run one disruption or display Chromium:

```bash
make run-eval EVAL_UI_ARGS="--scenario supply-chain-port-strike-la"
make run-eval EVAL_UI_ARGS="--headed"
```

To score the saved answers again without launching Playwright or sending new
requests to the dashboard/backend, use:

```bash
make rerun-eval-only
# Or select a specific source run:
make rerun-eval-only EVAL_SOURCE_RUN_ID=<source-mlflow-run-id>
```

By default, the target uses the newest local `evaluation-rows.jsonl` under
`EVAL_OUTPUT_DIR` (default `/tmp/supply-chain-agent-eval`). It creates a new
MLflow run in the source run's experiment and stores the new scores and metrics
as artifacts. It uses expectations saved with those rows and creates a fresh
evaluation trace for each answer, linked to its source trace. This keeps each
rerun's scores separate from older assessments without changing source traces.
It requires the evaluator Python environment created by
`make eval-ui-install`; it does not install or launch Chromium. The saved rows
must still be available on the machine that ran the original evaluation.

To download the artifacts for a run by its exact MLflow run name:

```bash
make download-eval EVAL_RUN_NAME='<mlflow-run-name>'
```

The target searches runs visible in the current MLflow workspace and downloads
the run's `evaluation/` artifacts to
`/tmp/supply-chain-agent-eval-artifacts/<run-name>-<run-id-prefix>/evaluation`.
Set `EVAL_DOWNLOAD_DIR` to choose another parent directory. The target uses the
MLflow tracking credentials from the active OpenShift context (or the explicit
`MLFLOW_TRACKING_TOKEN` and `MLFLOW_WORKSPACE` values) and requires the
evaluator Python environment. If more than one run has that exact name, it
downloads the most recent match.

The dataset defaults to `evaluation/ui/datasets/seeded-disruptions.json` and
contains Port Strike LA, Suez Blockage, and UK Airspace Closure. It can be
replaced with `--dataset <path>`. `EVAL_STORAGE_STATE` can point to a
Playwright storage-state file for an authenticated frontend; keep that file
outside version control.

Each seeded scenario includes a knowledge-base question with expected facts.
The evaluation row retains the KB text from the model prompt for review, and
the MLflow trace includes the retriever span so retrieval scorers assess the
same context that was supplied to the model.

## Results and review

The runner starts with the visible dashboard, applies the selected disruption,
records its impact snapshot and knowledge-base match, and enters each fixture
question in chat. It verifies the browser request contained the expected
scenario, impact snapshot, and vector-store selection. It timestamps each UI
chat request, then matches it to the backend chat trace by request time and
exact user question. A tool loop may produce multiple model-call spans in one
trace; the last text completion is used as the answer. The question and answer
passed to MLflow GenAI evaluation come from those runtime traces. The rendered
UI answer is retained in `scenario-results.json` for comparison.

The Port Strike scenario includes a general news-intent turn asking whether
anything in the news could affect the supply chain. The `expected_tool_used`
check accepts either `news_knowledge_base` or `fetch_news` for that broad
question; a plain-text pseudo tool call does not pass.

The experiment defaults to `supply-chain-disruption-evals` and can be changed
with `EVAL_MLFLOW_EXPERIMENT`. The MLflow run contains routed GenAI judge results
with standard metric names. `correctness` uses a `make_judge` scorer and routes
to the configured MaaS endpoint. Answer relevance is checked by MLflow's
built-in `RelevanceToQuery` judge under `builtin_relevance_to_query`. The run
also includes MLflow's built-in `Safety`, `RetrievalSufficiency`,
`RetrievalRelevance`, and `RetrievalGroundedness` judges under the `builtin_*`
names described above. Built-in retrieval relevance and
sufficiency run on KB-required turns and use the trace's `RETRIEVER` span.
Built-in retrieval groundedness runs only on KB-only questions because it
compares the whole answer with the retrieved context. Mixed impact/KB questions
use the custom source-aware groundedness judge. Judge-only reruns recreate the
retriever span from saved KB context. The duplicate built-in
`Correctness` judge is omitted; the custom correctness judge is retained for
all seeded questions, including rows with deterministic entity/value checks.
Impact-summary expectations include the total value and currency, while
highest-value expectations include the entity ID and individual value. If a
future row has no expected facts, correctness reports a scorer error instead of
silently producing a null result.
`retrieval_relevance`,
`retrieval_groundedness`, and `disruption_grounding` also use custom
`make_judge` instructions so they can distinguish KB evidence from
impact-snapshot facts. Retrieval relevance assesses
the retrieved KB context; retrieval groundedness checks whether answer claims
are supported by the appropriate evidence source. Retrieval checks use
`yes`/`no` judge values and include the judge's rationale on the evaluated
trace. They emit no assessment for turns that do not require KB retrieval.
`disruption_grounding`
checks claims against the impact snapshot and, for mixed-source turns, checks
KB facts against the retrieved KB context. It treats advice framed as something
to verify as a recommendation rather than a claim about current conditions, and
is not applicable to KB-only questions.
Custom checks measure non-empty answers, cross-scenario leakage, expected impact
values, the highest-value entity, and expected tool use. These code checks return
boolean feedback with rationales; checks that do not apply are marked not applicable.
The run also records UI and model-call latency metrics,
scenario IDs, fixture and impact-snapshot hashes, judge model, and backend
session metadata. It attempts to upload
`scenario-results.json`, `evaluation-rows.jsonl`, `openai-autolog-traces.json`,
`scored-answers.csv`, and `scorer-metrics.json` as run artifacts. When scorers
fail, it also prints each failed question, answer, and scorer rationale to the
console and uploads the same details in `failure-details.md`. Artifact upload
status is stored in the run tag `evaluation.artifact_upload_status`.
Both `make run-eval` and `make rerun-eval-only` return success only when every
applicable scorer result passes; skipped non-applicable checks do not count as
failures. A scorer failure returns a nonzero status after the results and metrics
are saved. The evaluation runner exits with status `1` for a failed evaluation.
GNU Make itself reports a failed recipe with process status `2`, as required by
its exit-code behavior.

Open the MLflow application in OpenShift AI, choose the application's project
workspace, and open the `supply-chain-disruption-evals` experiment. Compare
run metrics and tags, then open the run's Traces tab to review each evaluated
answer and scorer feedback. Open a retrieval assessment to read its rationale;
the same rationale is included in the `assessments` data in `scored-answers.csv`.
Download the run artifacts when the artifact
upload status is `uploaded`. The command prints the MLflow run ID at completion.

The harness does not save the browser trace because it can contain session
data. It saves a screenshot and partial scenario results in MLflow when a UI
run fails, subject to artifact upload support.

# Contributing

## Prerequisites

- [podman](https://podman.io/) (preferred over Docker)
- [OpenShift CLI (`oc`)](https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html) for cluster work
- [Helm](https://helm.sh/) 3.14+
- [pnpm](https://pnpm.io/) for the frontend
- Python 3.12+ for the backend / ingestion
- For Helm installs with general-simulation: a sibling checkout of [general-simulation](https://github.com/robertsandoval/general-simulation) at `../general-simulation` (see [helm/README.md](helm/README.md))

## Local development

1. Backend API (from `app/backend`): install deps and run Flask per the root [README.md](README.md).
2. Frontend (from `app/frontend`): `pnpm install` then `pnpm dev` (Vite proxies `/api`).
3. Full stack: Kind (`make helm-install-kind`) or OpenShift (`make helm-install` after `helm/secrets.yaml`).

There is no `podman-compose.yml` yet; use Kind or OpenShift for integrated runs.

## Quality checks

From the repository root:

```bash
make lint          # backend ruff/mypy + frontend eslint
make test          # backend pytest + frontend vitest
make pre-commit    # lint + test
make helm-test     # chart lint + helm-unittest
```

UI browser smoke (needs a running UI endpoint):

```bash
make e2e-ui-install
make e2e-ui
```

## Pull requests

- Prefer the `development` branch as the integration target unless the repo docs say otherwise.
- Keep PRs focused; see [tech_debt.md](tech_debt.md) for known cleanup already done or deferred.
- Include a short test plan (unit / helm / Kind smoke as relevant).
- Do not commit secrets (`helm/secrets.yaml`), local `helm/charts/*.tgz`, or `node_modules`.

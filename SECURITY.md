# Security Policy

## Supported Versions

pixplore is developed as a rolling project without tagged releases. Only the
latest commit on the `main` branch receives security updates. If you run a fork
or an older checkout, please update to `main` before reporting an issue.

| Version         | Supported          |
| --------------- | ------------------ |
| `main` (latest) | :white_check_mark: |
| older commits   | :x:                |

## Reporting a Vulnerability

Please report security vulnerabilities **privately** — do not open a public
issue for anything security-sensitive.

- Preferred: open a private report via GitHub Security Advisories
  (**Security → Advisories → Report a vulnerability** in this repository).
- Alternatively, open a regular issue that contains **no exploit details** and
  ask for a private channel.

When reporting, please include:

- affected component (e.g. `frontend`, `controller`, `pcloud-java`, `vectordb`),
- affected commit or deployment target (Docker Compose / Pulumi / GKE / Cloud Run),
- a description of the impact and, if possible, reproduction steps.

**Response expectations** (best effort — this is a personal project):

- acknowledgement within about 7 days,
- an initial assessment (accepted / needs-info / declined) within about 14 days,
- fixes for accepted issues merged to `main` as soon as practical, with credit
  in the advisory if you wish.

## Automated Scanning

This repository uses:

- **Dependabot** alerts for vulnerable dependencies,
- **CodeQL** code scanning for common code-level vulnerabilities,
- **pre-commit** hooks (ruff, pylint, YAML/TOML checks) enforced locally and in CI.

## Known Security Considerations

- **ChromaDB (`src/vectordb`):** The ChromaDB server runs a pinned version for
  which upstream has not yet released a patch for several advisories. Exposure is
  mitigated at the deployment layer: on GKE the service is `ClusterIP`
  (cluster-internal only), and on Cloud Run invocation is restricted via IAM to
  the frontend service account and the admin user. The server must not be exposed
  to untrusted networks, and `trust_remote_code` must not be enabled.
- **Client services (`frontend`, `controller`):** These connect to ChromaDB as
  clients. The `frontend` uses the lightweight `chromadb-client` package, which
  does not include the vulnerable server code.

## Handling Secrets

- Never commit credentials, tokens, or service-account keys. Use environment
  variables and Kubernetes/Cloud Run secrets (see `k8s/secret.yaml` and the
  Pulumi configuration).
- User-facing endpoints (e.g. the frontend on Cloud Run) are expected to be
  protected at the network/identity layer (IAM, Cloudflare Access).

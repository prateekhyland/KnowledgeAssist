# KnowledgeAssist — Cloud Edition

A multi-cloud deployment of the KnowledgeAssist API documentation assistant, with
**mixed public/private document retrieval**, **authenticated ingestion**, and
**encrypted code generation** for private context.

> This is the cloud variant of [`README.md`](README.md). The original is unchanged and
> remains the reference for single-machine, on-premise operation. Read that one if you
> are running on a VM with Ollama and a local index; read this one if you are deploying
> to Kubernetes on AWS, Azure, or a private plane.

---

## What changed from the on-premise edition

| Area | On-premise edition | Cloud edition |
|---|---|---|
| Deployment unit | One Windows/Linux VM | Kubernetes Deployment + Ingress + ingest Job |
| Targets | A machine you own | AWS EKS Auto Mode, Azure AKS Automatic, private K8s |
| Packaging | `scripts/run-api.ps1` | Container image + kustomize overlays or a Helm chart |
| Corpus | Uniformly public docs | Each source tagged `visibility` and `source_system` |
| Ingestion auth | Anonymous fetches | Bearer, custom header, or basic auth from env/secret manager |
| Config | `.env` + `sources.yaml` on disk | Kubernetes Secret + ConfigMap |
| Endpoints | `/chat`, `/config`, `/health` | adds **`/codegen`** with private-context encryption |
| Answer payload | `answer`, `sources` | adds `private_context`, per-source `visibility` / `source_system` |
| Data residency | Guaranteed by architecture | **A property of how you deploy it** — see below |

### The one claim that no longer holds automatically

The on-premise README states that everything runs on-premise with *"no cloud calls, no
telemetry."* In the cloud edition that is no longer an architectural guarantee. Your
documentation, your embeddings, and your model traffic live wherever you deploy them.

The cloud edition replaces that guarantee with **explicit controls**: sources are
labelled public or private, private credentials come from a cloud secret manager, and
code generated from private context is encrypted to a recipient key before it leaves the
service. Data residency becomes something you configure and verify per environment
rather than something the design enforces for you.

---

## Architecture

```
INGESTION (Kubernetes Job, re-run when docs change)
  sources (ConfigMap)
     -> resolve credentials from Secret / cloud secret manager
     -> crawl + parse (openapi | javadoc | html | sitemap | markdown)
     -> chunk -> embed -> PostgreSQL + pgvector
                          (rows carry visibility + source_system)

RUNTIME (Deployment behind an Ingress)
  /chat    question -> embed -> vector search -> rerank -> LLM -> answer + citations
                                                        -> private_context flag
  /codegen question -> same retrieval -> code-focused prompt -> LLM
                       -> if any source is private and encryption is on:
                          encrypt to recipient public key, return ciphertext only
```

| Layer | Component |
|---|---|
| API / RAG | Python + FastAPI, run by `uvicorn` in the container |
| LLM | Ollama-compatible endpoint via `OLLAMA_BASE_URL` (**external to these manifests**) |
| Vector store | PostgreSQL + `pgvector` (shared across environments is acceptable for a demo) |
| Secrets | Kubernetes Secret `knowledgeassist-env`, backed by Secrets Manager / Key Vault |
| Sources | ConfigMap `knowledgeassist-sources`, mounted at `/app/sources.yaml` |
| Ingress | nginx by default; patched per cloud (ALB on AWS) |

---

## Mixed public/private documentation

Every source in `sources.yaml` carries two labels, which are stored as columns on each
chunk and travel with it through retrieval into the answer:

- **`visibility`** — `public` or `private`. Defaults to `public`.
- **`source_system`** — where it came from: `confluence`, `sharepoint`, `git`,
  `website`, `javadoc`, `openapi`, …. Defaults to the source type.

```yaml
knowledge_bases:
  - id: default
    label: "My API"
    sources:
      - type: openapi
        url: https://docs.example.com/api/openapi.json
        visibility: public
        source_system: openapi

      - type: html
        url: https://private.example.com/guide/
        include: ["/guide/**"]
        visibility: private
        source_system: confluence
        auth_ref: PRIVATE_SOURCE_TOKEN_DOCS
```

At answer time the labels do three things. The prompt annotates each numbered context
block with its visibility, so the model can see which material is sensitive. Every
response includes a `private_context` boolean. And each citation carries its own
`visibility` and `source_system`, so a client can render provenance or suppress private
links.

See [`sources.example.yaml`](sources.example.yaml) for all supported patterns.

## Authenticated ingestion

Protected documentation is fetched using credentials resolved from the environment at
run time by `ingest/auth.py`. **No secret is ever written into `sources.yaml`** — the
YAML only names the environment variable to read.

| Pattern | Keys in `sources.yaml` | Result |
|---|---|---|
| Bearer token (default) | `auth_ref: ENV_NAME` | `Authorization: Bearer <token>` |
| Custom header | `auth_ref`, `auth_header: X-API-Key`, `auth_scheme: raw` | `X-API-Key: <token>` |
| Basic auth | `auth_type: basic`, `auth_user_env`, `auth_pass_env` | HTTP basic |
| Static non-secret headers | `headers: {Name: value}` | sent as-is |

Ingestion fails loudly if a referenced variable is missing or blank, rather than
silently fetching anonymously and indexing a login page.

## `/codegen` and private-context encryption

`/codegen` answers "write me the integration code for X" using the same retrieval path
as `/chat`, but with a code-focused prompt.

When **any** retrieved chunk is tagged `private` and
`ENABLE_PRIVATE_CODE_ENCRYPTION=true`, the generated code is **never returned in
plaintext**. Instead it is encrypted with a freshly generated Fernet data key, and that
data key is wrapped with the caller's RSA public key using OAEP/SHA-256:

```jsonc
{
  "private_context": true,
  "ciphertext":     "<base64 Fernet token>",
  "wrapped_key":    "<base64 RSA-OAEP wrapped data key>",
  "encryption_alg": "fernet+rsa-oaep-sha256",
  "key_id":         "demo-key",
  "sources":        [ ... ],
  "provenance":     [ { "n": 1, "url": "...", "visibility": "private",
                        "source_system": "confluence" } ]
}
```

Behaviour summary:

| Retrieved context | `recipient_public_key` | Response |
|---|---|---|
| Public only | not needed | plaintext `code` |
| Any private, encryption on | supplied | `ciphertext` + `wrapped_key`, **no `code` field** |
| Any private, encryption on | missing | **HTTP 400** |
| Any private, encryption off | — | plaintext `code`, `private_context: true` |

Decryption is the caller's job: unwrap the data key with your RSA private key, then open
the Fernet token.

---

## Deploying

### Prerequisites

- A Kubernetes cluster: EKS with Auto Mode, AKS Automatic, or any private cluster.
- A container registry: ECR, ACR, or your own.
- PostgreSQL 16+ with `pgvector`, reachable from the cluster over TLS.
- An Ollama-compatible model endpoint reachable at `OLLAMA_BASE_URL`.
- Secrets held in AWS Secrets Manager, Azure Key Vault, or an equivalent private store.

> **Before you start:** this repository does not yet contain a `Dockerfile`, and no
> Ollama workload is included in the manifests. Both must be supplied. See
> [Known gaps](#known-gaps-before-production).

### 1. Schema migration

The `visibility` and `source_system` columns and their indexes are added by an
idempotent migration that is safe to re-run on an existing database:

```powershell
./scripts/migrate-schema.ps1          # calls app.db.ensure_schema()
```

The equivalent raw DDL is [`sql/002_visibility_source_system.sql`](sql/002_visibility_source_system.sql).
Run it before the first cloud deployment and after any upgrade that changes the schema.

### 2. Configuration

Create the Secret the workloads read with `envFrom`:

```bash
kubectl create namespace knowledgeassist-app

kubectl -n knowledgeassist-app create secret generic knowledgeassist-env \
  --from-literal=PGHOST=... \
  --from-literal=PGPASSWORD=... \
  --from-literal=OLLAMA_BASE_URL=http://ollama.knowledgeassist-app:11434 \
  --from-literal=ENABLE_PRIVATE_CODE_ENCRYPTION=true \
  --from-literal=ENCRYPTION_KEY_ID=demo-key \
  --from-literal=PRIVATE_SOURCE_TOKEN_DOCS=...
```

Prefer a secret-store driver or External Secrets over `--from-literal`, which leaves
credentials in your shell history. On AWS, bind an IAM role to the service account to
read Secrets Manager; on Azure, bind a Managed Identity to read Key Vault.

Cloud-specific settings added by this edition (see [`.env.example`](.env.example)):

| Variable | Default | Purpose |
|---|---|---|
| `ENABLE_PRIVATE_CODE_ENCRYPTION` | `true` | Force encryption of private-context codegen |
| `ENCRYPTION_KEY_ID` | `demo-key` | Key identifier echoed in the response |
| `PRIVATE_SOURCE_TOKEN_*` | empty | Token values referenced by `auth_ref` |
| `PRIVATE_SOURCE_USER_*` / `_PASS_*` | empty | Basic-auth values for protected sources |

### 3. Deploy with kustomize

Three overlays sit on a shared base. Each sets the `knowledgeassist-app` namespace,
rewrites the image reference to that cloud's registry, and patches the Ingress with the
right ingress class and annotations.

```bash
kubectl apply -k k8s/overlays/aws        # ALB ingress, ECR image
kubectl apply -k k8s/overlays/azure      # Azure ingress, ACR image
kubectl apply -k k8s/overlays/private    # private plane
```

The base provides the Deployment (readiness and liveness probes on `/health`, 200m CPU
and 512Mi requested, 1 CPU and 1Gi limit), a ClusterIP Service on port 80 to container
port 8000, the Ingress with 300-second proxy read and send timeouts to accommodate slow
generations, the sources ConfigMap, and the ingest Job.

### 4. Deploy with Helm (alternative)

```bash
helm upgrade --install knowledgeassist helm/knowledgeassist \
  --namespace knowledgeassist-app --create-namespace \
  --set image.repository=<registry>/knowledgeassist \
  --set image.tag=demo-latest \
  --set ingress.host=knowledgeassist.example.com
```

The chart exposes `replicaCount`, `image`, `service`, `ingress`, `resources`,
`envSecret.existingSecretName`, an inline `sourcesConfig.yaml` rendered into a ConfigMap,
and `ingestJob`.

### 5. Index the documentation

The ingest Job mounts the sources ConfigMap at `/app/sources.yaml` and runs
`python -m ingest.index --sources /app/sources.yaml` with `restartPolicy: Never` and
`backoffLimit: 1`. Re-run it whenever the docs change:

```bash
kubectl -n knowledgeassist-app delete job knowledgeassist-ingest --ignore-not-found
kubectl -n knowledgeassist-app apply -k k8s/overlays/aws
kubectl -n knowledgeassist-app logs job/knowledgeassist-ingest -f
```

### 6. Validate

```powershell
./scripts/demo-api-tests.ps1 -BaseUrl https://knowledgeassist.example.com
```

The cutover gates that must pass in every environment:

1. `GET /health` returns `status=ok` with `llm=true` and `db=true`.
2. A public-only `/chat` question returns an answer with citations and `private_context=false`.
3. A private or mixed `/chat` question returns `private_context=true`.
4. A private or mixed `/codegen` call **with** a key returns `ciphertext` and `wrapped_key` and no plaintext code.
5. The same call **without** a key returns HTTP 400.
6. A domain-specific prompt returns content genuinely grounded in your ingested docs — confirming `OLLAMA_BASE_URL` points at a real model and not a stub.

### 7. Rollback

```bash
kubectl -n knowledgeassist-app rollout status  deploy/knowledgeassist-api
kubectl -n knowledgeassist-app rollout undo    deploy/knowledgeassist-api
```

Roll back if `db=false` or `llm=false` persists beyond five minutes, if `/codegen` ever
returns plaintext while `private_context=true`, or if private-source ingestion fails on
secrets or auth.

---

## Known gaps before production

These are real and worth planning for; none is hidden by the manifests.

- **No `Dockerfile` is committed.** Every manifest references `REPLACE_IMAGE` or
  `REPLACE_IMAGE_REPO`, and the runbook assumes CodeBuild or ACR Tasks builds the image.
  The build recipe itself still has to be written and pinned.
- **No Ollama workload is included.** The Deployment runs only the API.
  `OLLAMA_BASE_URL` must point at a model service you deploy and size separately,
  including its GPU scheduling.
- **The API is unauthenticated.** There is no authentication or rate limiting on `/chat`
  or `/codegen`, and the Ingress is internet-facing by default. Put a gateway, WAF, or
  authenticating proxy in front of it, and restrict egress with a NetworkPolicy.
- **Encryption protects the response, not the retrieval.** `/chat` still returns private
  content as plaintext prose; only `/codegen` output is encrypted. Anyone who can reach
  the endpoint can read private documentation through `/chat`.
- **Single replica, no autoscaling.** `replicaCount: 1` with no HPA or PodDisruptionBudget,
  and a 1 CPU / 1Gi limit. Generations are slow, so plan concurrency deliberately.
- **No automated tests on this branch.** The `tests/` tree and the retrieval-quality work
  (stemming, heading-aware chunking, the tuned lexical weight, the cached vector store)
  live on `develop` and have not been merged here. Merge before relying on either.
- **Local mode on this branch reads only the first shard** of `data/index.pkl`, so a
  knowledge base appended by a later ingest run is invisible. This affects local mode
  only; pgvector deployments are unaffected.

## Related documents

- [`DEPLOYMENT_DEMO_MULTI_CLOUD.md`](DEPLOYMENT_DEMO_MULTI_CLOUD.md) — target platforms and demo validation plan
- [`CLOUD_CUTOVER_CHECKLIST.md`](CLOUD_CUTOVER_CHECKLIST.md) — per-cloud cutover checklist and rollback triggers
- [`CLOUD_CUTOVER_RUNBOOK_COMMANDS.md`](CLOUD_CUTOVER_RUNBOOK_COMMANDS.md) — copy-paste command sheet per cloud
- [`k8s/README.md`](k8s/README.md) and [`helm/knowledgeassist/README.md`](helm/knowledgeassist/README.md) — manifest and chart usage
- [`docs/PRESENTATION-CLOUD.md`](docs/PRESENTATION-CLOUD.md) — the talk-track version of this material

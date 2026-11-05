# Cloud Cutover Checklist (EKS Auto + AKS Automatic)

This checklist is for deploying the current KnowledgeAssist demo build to AWS and Azure with mixed public/private doc support and private-context encrypted codegen.

## 1) Common pre-cutover (both clouds)

- [ ] Finalize runtime env vars from [.env.example](C:/Users/pbose/Git/KnowledgeAssist/.env.example).
- [ ] Ensure `ENABLE_PRIVATE_CODE_ENCRYPTION=true` and `ENCRYPTION_KEY_ID` are set.
- [ ] Store private source credentials in cloud secret managers (no plaintext in manifests).
- [ ] Confirm DB endpoint (PostgreSQL + pgvector) is reachable with TLS.
- [ ] Apply schema migration with [migrate-schema.ps1](C:/Users/pbose/Git/KnowledgeAssist/scripts/migrate-schema.ps1) or equivalent startup migration.
- [ ] Confirm code includes [main.py](C:/Users/pbose/Git/KnowledgeAssist/app/main.py), [db.py](C:/Users/pbose/Git/KnowledgeAssist/app/db.py), [crypto.py](C:/Users/pbose/Git/KnowledgeAssist/app/crypto.py), [retriever.py](C:/Users/pbose/Git/KnowledgeAssist/app/retriever.py).

## 2) AWS cutover checklist (EKS Auto)

- [ ] Create/verify EKS cluster with Auto Mode enabled.
- [ ] Create ECR repository for KnowledgeAssist image.
- [ ] Build image in AWS CodeBuild/GitHub Actions and push to ECR.
- [ ] Deploy app manifests/Helm chart into `knowledgeassist-app` namespace.
- [ ] Configure IAM role for service account to read Secrets Manager entries.
- [ ] Set deployment env vars (`PG*`, `OLLAMA_*`, encryption flags).
- [ ] Expose ingress/service and verify TLS endpoint.
- [ ] Run ingest workload using [ingest.ps1](C:/Users/pbose/Git/KnowledgeAssist/scripts/ingest.ps1) equivalent job.
- [ ] Verify `/health` reports `db=true` and `llm=true`.

## 3) Azure cutover checklist (AKS Automatic)

- [ ] Create/verify AKS Automatic cluster.
- [ ] Create ACR repository for KnowledgeAssist image.
- [ ] Build image in ACR Tasks/GitHub Actions and push to ACR.
- [ ] Deploy same manifests with Azure overlay into `knowledgeassist-app` namespace.
- [ ] Bind Managed Identity to read Key Vault secrets.
- [ ] Set deployment env vars (`PG*`, `OLLAMA_*`, encryption flags).
- [ ] Expose ingress/service and verify TLS endpoint.
- [ ] Run ingest workload job against configured sources.
- [ ] Verify `/health` reports `db=true` and `llm=true`.

## 4) Private-plane checklist (Lightsail simulation or true private cloud)

- [ ] Deploy same app version in private plane cluster.
- [ ] Use private secret store for private-source credentials.
- [ ] Configure sources with `visibility: private` where appropriate in [sources.example.yaml](C:/Users/pbose/Git/KnowledgeAssist/sources.example.yaml)-compatible format.
- [ ] Confirm private docs are ingested and tagged correctly.
- [ ] Confirm mixed retrieval returns `private_context=true` when private chunks are included.

## 5) Cutover validation gates (must pass)

- [ ] `GET /health` -> `status=ok`, `llm=true`, `db=true`.
- [ ] Public-only `/chat` -> valid answer + citations + `private_context=false`.
- [ ] Private/mixed `/chat` -> valid answer + `private_context=true`.
- [ ] Private/mixed `/codegen` with key -> returns `ciphertext` + `wrapped_key` + no plaintext code.
- [ ] Private/mixed `/codegen` without key -> HTTP 400.
- [ ] Run [demo-api-tests.ps1](C:/Users/pbose/Git/KnowledgeAssist/scripts/demo-api-tests.ps1) against each environment endpoint.

## 6) Rollback triggers

- [ ] `db=false` or `llm=false` persists for >5 minutes.
- [ ] `/codegen` returns plaintext code when `private_context=true`.
- [ ] Ingestion fails for private sources due to secret/auth issues.
- [ ] Error rate or timeout rate exceeds agreed demo threshold.

## 7) Post-cutover monitoring (first 24 hours)

- [ ] Track `/health` every 1-5 minutes.
- [ ] Monitor ingestion job success/failure counts.
- [ ] Monitor codegen request outcomes and encryption path usage.
- [ ] Review logs for secret leakage indicators (must be none).

## 8) Current docs and scripts

- Architecture plan: [DEPLOYMENT_DEMO_MULTI_CLOUD.md](C:/Users/pbose/Git/KnowledgeAssist/DEPLOYMENT_DEMO_MULTI_CLOUD.md)
- Schema files: [001_init.sql](C:/Users/pbose/Git/KnowledgeAssist/sql/001_init.sql), [002_visibility_source_system.sql](C:/Users/pbose/Git/KnowledgeAssist/sql/002_visibility_source_system.sql)
- Migration script: [migrate-schema.ps1](C:/Users/pbose/Git/KnowledgeAssist/scripts/migrate-schema.ps1)
- Test script: [demo-api-tests.ps1](C:/Users/pbose/Git/KnowledgeAssist/scripts/demo-api-tests.ps1)
- API entrypoint: [main.py](C:/Users/pbose/Git/KnowledgeAssist/app/main.py)

## 9) Real model/backend verification per cloud

### AWS (EKS Auto)

- [ ] Confirm `OLLAMA_BASE_URL`/model endpoint points to real model service (not a stub).
- [ ] Run [demo-api-tests.ps1](C:/Users/pbose/Git/KnowledgeAssist/scripts/demo-api-tests.ps1) against AWS ingress URL.
- [ ] Run a domain-specific prompt and verify answer content is grounded in your ingested docs.
- [ ] Run private-context `/codegen` and verify encrypted payload is returned (no plaintext code field).

### Azure (AKS Automatic)

- [ ] Confirm `OLLAMA_BASE_URL`/model endpoint points to real model service (not a stub).
- [ ] Run [demo-api-tests.ps1](C:/Users/pbose/Git/KnowledgeAssist/scripts/demo-api-tests.ps1) against Azure ingress URL.
- [ ] Run a domain-specific prompt and verify answer content is grounded in your ingested docs.
- [ ] Run private-context `/codegen` and verify encrypted payload is returned (no plaintext code field).

### Private plane

- [ ] Confirm model endpoint and private-source credentials are loaded from private secret store.
- [ ] Run [demo-api-tests.ps1](C:/Users/pbose/Git/KnowledgeAssist/scripts/demo-api-tests.ps1) against private ingress URL.
- [ ] Verify private-source ingestion succeeds for auth-protected docs.
- [ ] Verify private-context `/codegen` encryption path and provenance metadata.

# Helm chart: knowledgeassist

Minimal Helm chart for KnowledgeAssist demo deployment (API + optional ingest job).

## Quick start

```powershell
# Example install
helm upgrade --install ka-demo ./helm/knowledgeassist \
  --namespace knowledgeassist-app --create-namespace \
  --set image.repository=<registry>/knowledgeassist \
  --set image.tag=demo-latest \
  --set ingress.host=<your-host> \
  --set ingress.className=<ingress-class>
```

## Required pre-step

Create the runtime env secret first:

```powershell
kubectl -n knowledgeassist-app create secret generic knowledgeassist-env \
  --from-literal=PGHOST=<pg-host> \
  --from-literal=PGPORT=5432 \
  --from-literal=PGDATABASE=<pg-db> \
  --from-literal=PGUSER=<pg-user> \
  --from-literal=PGPASSWORD=<pg-password> \
  --from-literal=OLLAMA_BASE_URL=<model-endpoint> \
  --from-literal=LLM_MODEL=<model-name> \
  --from-literal=ENABLE_PRIVATE_CODE_ENCRYPTION=true \
  --from-literal=ENCRYPTION_KEY_ID=demo-key \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Cloud examples

- EKS Auto: `--set ingress.className=alb`
- AKS Automatic: `--set ingress.className=webapprouting.kubernetes.azure.com`
- Private plane (nginx): `--set ingress.className=nginx`

## Ingest job

- Enabled by default (`ingestJob.enabled=true`).
- To disable during initial rollout:

```powershell
helm upgrade --install ka-demo ./helm/knowledgeassist \
  --namespace knowledgeassist-app --create-namespace \
  --set ingestJob.enabled=false
```

# Cloud Cutover Runbook Command Sheet

This is a copy-paste oriented command sheet for demo cutover.

> Replace placeholders like `<...>` before running.

## 0) Local prechecks (repo root)

```powershell
cd C:/Users/pbose/Git/KnowledgeAssist
py -3 --version
```

```powershell
# Create venv and install dependencies
py -3 -m venv .venv
./.venv/Scripts/pip.exe install -r requirements.txt
```

```powershell
# Apply schema migration against target DB settings from .env / env vars
./scripts/migrate-schema.ps1
```

```powershell
# Ingest docs (after preparing sources.yaml)
Copy-Item sources.example.yaml sources.yaml -Force
# edit sources.yaml with real URLs + visibility + auth_ref
./scripts/ingest.ps1
```

## 1) AWS (EKS Auto) commands

```powershell
# Authenticate AWS CLI
aws configure
aws sts get-caller-identity
```

```powershell
# Variables
$AWS_REGION = "<region>"
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$EKS_CLUSTER = "<eks-cluster-name>"
$ECR_REPO = "knowledgeassist"
$IMAGE_TAG = "demo-<yyyymmdd-hhmm>"
```

```powershell
# ECR repo (idempotent)
aws ecr describe-repositories --repository-names $ECR_REPO --region $AWS_REGION 2>$null
if ($LASTEXITCODE -ne 0) {
  aws ecr create-repository --repository-name $ECR_REPO --region $AWS_REGION
}
```

```powershell
# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

```powershell
# Build + push image (if Docker available in CI/runner)
docker build -t "$ECR_REPO:$IMAGE_TAG" .
docker tag "$ECR_REPO:$IMAGE_TAG" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG"
```

```powershell
# kubeconfig for EKS
aws eks update-kubeconfig --name $EKS_CLUSTER --region $AWS_REGION
kubectl get nodes
```

```powershell
# Namespace + secret placeholders
kubectl create namespace knowledgeassist-app --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace knowledgeassist-jobs --dry-run=client -o yaml | kubectl apply -f -
```

```powershell
# Example env secret (replace values)
kubectl -n knowledgeassist-app create secret generic knowledgeassist-env \
  --from-literal=PGHOST="<pg-host>" \
  --from-literal=PGPORT="5432" \
  --from-literal=PGDATABASE="<pg-db>" \
  --from-literal=PGUSER="<pg-user>" \
  --from-literal=PGPASSWORD="<pg-password>" \
  --from-literal=OLLAMA_BASE_URL="<model-endpoint>" \
  --from-literal=LLM_MODEL="<model-name>" \
  --from-literal=ENABLE_PRIVATE_CODE_ENCRYPTION="true" \
  --from-literal=ENCRYPTION_KEY_ID="demo-key" \
  --dry-run=client -o yaml | kubectl apply -f -
```

```powershell
# Deploy manifests/chart (replace path)
kubectl -n knowledgeassist-app apply -f <k8s-manifests-path>
kubectl -n knowledgeassist-app get pods,svc,ingress
```

## 2) Azure (AKS Automatic) commands

```powershell
# Login
az login
az account set --subscription "<subscription-id-or-name>"
```

```powershell
# Variables
$AZ_RG = "<resource-group>"
$AKS_CLUSTER = "<aks-cluster-name>"
$ACR_NAME = "<acrNameNoHyphen>"
$IMAGE_NAME = "knowledgeassist"
$IMAGE_TAG = "demo-<yyyymmdd-hhmm>"
```

```powershell
# ACR login
az acr login --name $ACR_NAME
```

```powershell
# Build and push via ACR Tasks (no local Docker needed)
az acr build --registry $ACR_NAME --image "$IMAGE_NAME:$IMAGE_TAG" .
```

```powershell
# Get AKS credentials
az aks get-credentials --resource-group $AZ_RG --name $AKS_CLUSTER --overwrite-existing
kubectl get nodes
```

```powershell
# Namespaces
kubectl create namespace knowledgeassist-app --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace knowledgeassist-jobs --dry-run=client -o yaml | kubectl apply -f -
```

```powershell
# Example env secret (replace values)
kubectl -n knowledgeassist-app create secret generic knowledgeassist-env \
  --from-literal=PGHOST="<pg-host>" \
  --from-literal=PGPORT="5432" \
  --from-literal=PGDATABASE="<pg-db>" \
  --from-literal=PGUSER="<pg-user>" \
  --from-literal=PGPASSWORD="<pg-password>" \
  --from-literal=OLLAMA_BASE_URL="<model-endpoint>" \
  --from-literal=LLM_MODEL="<model-name>" \
  --from-literal=ENABLE_PRIVATE_CODE_ENCRYPTION="true" \
  --from-literal=ENCRYPTION_KEY_ID="demo-key" \
  --dry-run=client -o yaml | kubectl apply -f -
```

```powershell
# Deploy manifests/chart (replace path)
kubectl -n knowledgeassist-app apply -f <k8s-manifests-path>
kubectl -n knowledgeassist-app get pods,svc,ingress
```

## 3) Private plane commands (Lightsail simulation or true private K8s)

```powershell
# kubeconfig context should point to private plane
kubectl config current-context
kubectl get nodes
```

```powershell
kubectl create namespace knowledgeassist-app --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace knowledgeassist-jobs --dry-run=client -o yaml | kubectl apply -f -
```

```powershell
# Apply private-specific deployment settings (replace path)
kubectl -n knowledgeassist-app apply -f <private-k8s-manifests-path>
kubectl -n knowledgeassist-app get pods,svc,ingress
```

## 4) Runtime validation commands

```powershell
# Set endpoint for target environment
$BASE_URL = "https://<env-endpoint>"
```

```powershell
# Health check
Invoke-RestMethod -Method GET -Uri "$BASE_URL/health" | ConvertTo-Json -Depth 10
```

```powershell
# Chat smoke test
$chat = @{ question = "How do I sync private orders?"; kb_id = "default" } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri "$BASE_URL/chat" -ContentType "application/json" -Body $chat | ConvertTo-Json -Depth 10
```

```powershell
# Full demo test pack
./scripts/demo-api-tests.ps1 -BaseUrl $BASE_URL -KbId default
```

## 5) Fast rollback commands

```powershell
# Rollout status
kubectl -n knowledgeassist-app rollout status deployment/<deployment-name>
```

```powershell
# Roll back
kubectl -n knowledgeassist-app rollout undo deployment/<deployment-name>
```

```powershell
# Verify after rollback
kubectl -n knowledgeassist-app get pods
Invoke-RestMethod -Method GET -Uri "$BASE_URL/health" | ConvertTo-Json -Depth 10
```

## Related docs

- [CLOUD_CUTOVER_CHECKLIST.md](C:/Users/pbose/Git/KnowledgeAssist/CLOUD_CUTOVER_CHECKLIST.md)
- [DEPLOYMENT_DEMO_MULTI_CLOUD.md](C:/Users/pbose/Git/KnowledgeAssist/DEPLOYMENT_DEMO_MULTI_CLOUD.md)
- [demo-api-tests.ps1](C:/Users/pbose/Git/KnowledgeAssist/scripts/demo-api-tests.ps1)
- [migrate-schema.ps1](C:/Users/pbose/Git/KnowledgeAssist/scripts/migrate-schema.ps1)

## 6) Use bundled Kubernetes starter manifests

```powershell
# AWS overlay
kubectl apply -k k8s/overlays/aws

# Azure overlay
kubectl apply -k k8s/overlays/azure

# Private overlay
kubectl apply -k k8s/overlays/private
```

See [k8s/README.md](C:/Users/pbose/Git/KnowledgeAssist/k8s/README.md) for required pre-edit steps.

## 7) Optional Helm-based deployment

```powershell
helm upgrade --install ka-demo ./helm/knowledgeassist \
  --namespace knowledgeassist-app --create-namespace \
  --set image.repository=<registry>/knowledgeassist \
  --set image.tag=<tag> \
  --set ingress.host=<host> \
  --set ingress.className=<ingress-class>
```

See [helm/knowledgeassist/README.md](C:/Users/pbose/Git/KnowledgeAssist/helm/knowledgeassist/README.md).

## 8) Real backend verification prompts (per environment)

```powershell
# Set one environment at a time
$BASE_URL = "https://<aws-or-azure-or-private-endpoint>"

# Health (must show llm=true and db=true)
Invoke-RestMethod -Method GET -Uri "$BASE_URL/health" | ConvertTo-Json -Depth 8

# Domain-grounded chat prompt
$chat = @{ question = "Explain the private order sync endpoint and required auth headers"; kb_id = "default" } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri "$BASE_URL/chat" -ContentType "application/json" -Body $chat | ConvertTo-Json -Depth 12

# Full scripted verification (includes encrypted /codegen expectation)
./scripts/demo-api-tests.ps1 -BaseUrl $BASE_URL -KbId default -ChatQuestion "How do I sync private orders?" -CodegenQuestion "Generate Python code to sync private orders to a public product catalog."
```

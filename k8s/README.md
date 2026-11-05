# Kubernetes Starter Manifests

This folder provides a minimal deploy pack for the demo.

## Structure

- `base/`: common resources
  - `Deployment` (`knowledgeassist-api`)
  - `Service` (`knowledgeassist-api`)
  - `Ingress` (`knowledgeassist-api`)
  - `Job` (`knowledgeassist-ingest`)
  - `ConfigMap` (`knowledgeassist-sources`)
- `overlays/aws`: EKS Auto customization
- `overlays/azure`: AKS Automatic customization
- `overlays/private`: private-plane customization

## Apply

```powershell
# AWS
kubectl apply -k k8s/overlays/aws

# Azure
kubectl apply -k k8s/overlays/azure

# Private
kubectl apply -k k8s/overlays/private
```

## Required edits before apply

1. Update image references in each overlay `kustomization.yaml`.
2. Create secret `knowledgeassist-env` in `knowledgeassist-app` namespace.
3. Replace host in `base/ingress.yaml` if needed.
4. Replace `sources.yaml` content in `base/sources-configmap.yaml` (or override via your own ConfigMap).

## Run ingestion job manually

```powershell
kubectl -n knowledgeassist-app delete job knowledgeassist-ingest --ignore-not-found
kubectl -n knowledgeassist-app create job --from=job/knowledgeassist-ingest knowledgeassist-ingest-manual
kubectl -n knowledgeassist-app logs -f job/knowledgeassist-ingest-manual
```

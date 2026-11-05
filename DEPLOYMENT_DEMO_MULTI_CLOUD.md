# Multi-Cloud Demo Deployment Plan

This document captures the practical same-day deployment model for KnowledgeAssist across AWS, Azure, and a private plane simulation.

## Target Platforms

- AWS: EKS Auto Mode
- Azure: AKS Automatic
- Private plane:
  - Demo simulation: Kubernetes on Lightsail instances
  - True private: on-prem/private Kubernetes

## Runtime Behavior

- `/chat` supports mixed public/private retrieval.
- `/codegen` supports integration code generation.
- If any retrieved source is tagged `private` and encryption is enabled, `/codegen` returns encrypted output only.

## Security Baseline

- Source-level tags: `visibility` and `source_system`.
- Private source credentials loaded from environment/secret managers at runtime.
- No hardcoded credentials.
- Private-context code responses require `recipient_public_key`.

## Required Environment Flags

- `ENABLE_PRIVATE_CODE_ENCRYPTION=true`
- `ENCRYPTION_KEY_ID=demo-key`
- `PRIVATE_SOURCE_TOKEN_*` values injected per environment.

## Deployment Notes

- Use cloud-native builds (CodeBuild/ECR, ACR Tasks/ACR) if local Docker is unavailable.
- Deploy the same application manifests with cloud-specific overlays.
- For demo speed, a shared pgvector database is acceptable.

## Demo Validation

1. Public-only question returns plaintext response.
2. Private-only question marks `private_context=true`.
3. Mixed `/codegen` request returns encrypted payload.
4. Missing key for private-context `/codegen` returns HTTP 400.

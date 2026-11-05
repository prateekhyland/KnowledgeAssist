"""Authentication helpers for ingestion connectors."""
from __future__ import annotations

import os
from typing import Any


AuthTuple = tuple[str, str] | None


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"Required credential env var '{name}' is not set.")
    return value.strip()


def resolve_request_auth(src: dict[str, Any]) -> tuple[dict[str, str], AuthTuple]:
    """Return `(headers, auth)` for HTTP source fetches.

    Supported source config patterns:
    - auth_ref: ENV_VAR_WITH_TOKEN
      (defaults to Authorization: Bearer <token>)
    - auth_ref + auth_header (+ auth_scheme=raw|bearer)
    - auth_type: basic + auth_user_env + auth_pass_env
    - headers: {Header-Name: value} for non-secret static headers
    """
    headers: dict[str, str] = {}
    auth: AuthTuple = None

    # Optional non-secret static headers from sources.yaml
    static_headers = src.get("headers") or {}
    if isinstance(static_headers, dict):
        for key, value in static_headers.items():
            if value is None:
                continue
            headers[str(key)] = str(value)

    auth_type = str(src.get("auth_type", "")).strip().lower()

    if auth_type == "basic":
        user_env = src.get("auth_user_env")
        pass_env = src.get("auth_pass_env")
        if not user_env or not pass_env:
            raise ValueError(
                "auth_type=basic requires auth_user_env and auth_pass_env in source config."
            )
        auth = (_require_env(str(user_env)), _require_env(str(pass_env)))
        return headers, auth

    auth_ref = src.get("auth_ref")
    if auth_ref:
        token = _require_env(str(auth_ref))
        auth_header = str(src.get("auth_header", "Authorization")).strip() or "Authorization"
        auth_scheme = str(src.get("auth_scheme", "bearer")).strip().lower()
        if auth_scheme == "raw":
            headers[auth_header] = token
        else:
            headers[auth_header] = f"Bearer {token}"

    return headers, auth

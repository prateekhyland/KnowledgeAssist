"""Parse OpenAPI/Swagger specs into operation-level chunks."""
from __future__ import annotations

from typing import Any

import yaml

from .chunk import Chunk
from .crawl import AuthType, fetch_text

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def _load_spec(
    url: str,
    headers: dict[str, str] | None = None,
    auth: AuthType = None,
) -> dict[str, Any]:
    raw = fetch_text(url, headers=headers, auth=auth)
    try:
        return yaml.safe_load(raw) or {}
    except Exception:
        return {}


def _resolve_ref(spec: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        return {}
    node: Any = spec
    for part in ref[2:].split("/"):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return {}
    return node if isinstance(node, dict) else {}


def _schema_summary(spec: dict, schema: dict, depth: int = 0) -> str:
    """Render a compact, human-readable schema description."""
    if not schema or depth > 3:
        return ""
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        resolved = _resolve_ref(spec, schema["$ref"])
        inner = _schema_summary(spec, resolved, depth + 1)
        return f"{name}{(': ' + inner) if inner else ''}"
    t = schema.get("type")
    if t == "array":
        return f"array of {_schema_summary(spec, schema.get('items', {}), depth + 1)}"
    if t == "object" or "properties" in schema:
        props = schema.get("properties", {})
        parts = []
        for pname, pschema in props.items():
            parts.append(f"{pname} ({_schema_summary(spec, pschema, depth + 1)})")
        return "{ " + ", ".join(parts) + " }" if parts else "object"
    return t or "any"


def parse(
    url: str,
    kb_id: str,
    headers: dict[str, str] | None = None,
    auth: AuthType = None,
) -> list[Chunk]:
    spec = _load_spec(url, headers=headers, auth=auth)
    chunks: list[Chunk] = []
    base_title = spec.get("info", {}).get("title", "API")

    for path, path_item in (spec.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        common_params = path_item.get("parameters", [])
        for method, op in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(op, dict):
                continue

            lines: list[str] = []
            summary = op.get("summary", "")
            description = op.get("description", "")
            op_id = op.get("operationId", "")
            tags = ", ".join(op.get("tags", []))

            header = f"{method.upper()} {path}"
            lines.append(header)
            if summary:
                lines.append(f"Summary: {summary}")
            if op_id:
                lines.append(f"operationId: {op_id}")
            if tags:
                lines.append(f"Tags: {tags}")
            if description:
                lines.append(f"\n{description}")

            # Parameters
            params = list(common_params) + list(op.get("parameters", []))
            if params:
                lines.append("\nParameters:")
                for prm in params:
                    if "$ref" in prm:
                        prm = _resolve_ref(spec, prm["$ref"])
                    name = prm.get("name", "?")
                    loc = prm.get("in", "")
                    required = " (required)" if prm.get("required") else ""
                    pdesc = prm.get("description", "")
                    ptype = _schema_summary(spec, prm.get("schema", {}))
                    lines.append(f"- {name} [{loc}]{required} {ptype}: {pdesc}".rstrip())

            # Request body
            rb = op.get("requestBody")
            if isinstance(rb, dict):
                if "$ref" in rb:
                    rb = _resolve_ref(spec, rb["$ref"])
                content = rb.get("content", {})
                for media, mobj in content.items():
                    schema = mobj.get("schema", {})
                    lines.append(
                        f"\nRequest body ({media}): {_schema_summary(spec, schema)}"
                    )

            # Responses
            responses = op.get("responses", {})
            if responses:
                lines.append("\nResponses:")
                for code, robj in responses.items():
                    if isinstance(robj, dict) and "$ref" in robj:
                        robj = _resolve_ref(spec, robj["$ref"])
                    rdesc = robj.get("description", "") if isinstance(robj, dict) else ""
                    schema_txt = ""
                    if isinstance(robj, dict):
                        for media, mobj in (robj.get("content") or {}).items():
                            schema_txt = (
                                f" -> {media}: "
                                f"{_schema_summary(spec, mobj.get('schema', {}))}"
                            )
                            break
                    lines.append(f"- {code}: {rdesc}{schema_txt}".rstrip())

            title = summary or op_id or header
            chunks.append(
                Chunk(
                    kb_id=kb_id,
                    api_set="openapi",
                    source_url=url,
                    title=f"{base_title}: {title}",
                    content="\n".join(lines),
                    metadata={
                        "method": method.upper(),
                        "path": path,
                        "operationId": op_id,
                        "tags": op.get("tags", []),
                    },
                )
            )
    return chunks

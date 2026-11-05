"""Prompt construction for grounded answers + code samples."""
from __future__ import annotations

SYSTEM_PROMPT = """You are {app_name}, an assistant that helps developers use an API \
based strictly on its official documentation.

Rules:
- Answer ONLY using the provided documentation context below. Do not invent method \
names, endpoints, parameters, or fields that are not present in the context.
- If the context does not contain the answer, say you couldn't find it in the docs and \
suggest what the user might search for instead. Never guess.
- When you show code, prefer complete, runnable snippets that use the exact class names, \
methods, endpoints, and parameters found in the context.
- Cite your sources: reference the numbered [n] context sources you used, and list them.
- Be concise and technical. Use Markdown, with fenced code blocks for code.
"""

CODEGEN_SYSTEM_PROMPT = """You are {app_name}, an assistant that writes integration code \
based strictly on the provided API documentation context.

Rules:
- Use ONLY APIs and fields present in the provided context.
- Generate practical, runnable code where possible.
- If important details are missing, state assumptions clearly before code.
- Include a short 'Sources' section with [n] references you actually used.
"""


def build_context(sources: list[dict]) -> str:
    """Render retrieved chunks into a numbered context block."""
    blocks = []
    for i, s in enumerate(sources, start=1):
        title = s.get("title") or s.get("api_set", "doc")
        url = s.get("source_url", "")
        visibility = s.get("visibility", "public")
        blocks.append(
            f"[{i}] {title} ({visibility})\nURL: {url}\n---\n{s['content'].strip()}"
        )
    return "\n\n".join(blocks)


def build_messages(question: str, sources: list[dict], app_name: str) -> list[dict]:
    context = build_context(sources)
    user = (
        f"Documentation context:\n\n{context}\n\n"
        f"----\n\nUser question: {question}\n\n"
        "Answer using only the context above. Include a 'Sources' section listing the "
        "[n] references (with their URLs) that you actually used."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT.format(app_name=app_name)},
        {"role": "user", "content": user},
    ]


def build_codegen_messages(question: str, sources: list[dict], app_name: str) -> list[dict]:
    """Build code-focused prompt messages from the retrieved context."""
    context = build_context(sources)
    user = (
        f"Documentation context:\n\n{context}\n\n"
        "----\n\n"
        f"Integration/code request: {question}\n\n"
        "Generate implementation-focused code from the context above. "
        "If details are missing, call them out and keep the code conservative. "
        "Include a 'Sources' section listing the [n] references with URLs."
    )
    return [
        {"role": "system", "content": CODEGEN_SYSTEM_PROMPT.format(app_name=app_name)},
        {"role": "user", "content": user},
    ]

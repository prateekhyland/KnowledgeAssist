"""KnowledgeAssist FastAPI application: chat API + widget + standalone UI."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from . import llm, prompts
from . import store as db
from .config import get_settings
from .crypto import encrypt_payload
from .retriever import has_private_context, retrieve

settings = get_settings()
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    kb_id: str | None = None
    api_set: str | None = None
    stream: bool = False


class CodegenRequest(BaseModel):
    question: str
    recipient_public_key: str | None = None
    kb_id: str | None = None
    api_set: str | None = None



def _sources_payload(sources: list[dict]) -> list[dict]:
    """Trim retrieved chunks to what the client needs for citations."""
    out = []
    for i, s in enumerate(sources, start=1):
        out.append(
            {
                "n": i,
                "title": s.get("title"),
                "url": s.get("source_url"),
                "api_set": s.get("api_set"),
                "visibility": s.get("visibility", "public"),
                "source_system": s.get("source_system", s.get("api_set")),
                "score": round(s.get("rerank_score", s.get("score", 0.0)), 4),
            }
        )
    return out


@app.get("/health")
def health() -> JSONResponse:
    ok_llm = llm.health()
    try:
        db.list_knowledge_bases()
        ok_db = True
    except Exception:
        ok_db = False
    status = "ok" if (ok_llm and ok_db) else "degraded"
    return JSONResponse(
        {"status": status, "llm": ok_llm, "db": ok_db, "app": settings.app_name}
    )


@app.get("/config")
def config() -> dict:
    """Public config for the widget/UI (name + available knowledge bases)."""
    try:
        kbs = db.list_knowledge_bases()
    except Exception:
        kbs = []
    return {"app_name": settings.app_name, "knowledge_bases": kbs}


@app.post("/chat")
def chat(req: ChatRequest):
    sources = retrieve(req.question, kb_id=req.kb_id, api_set=req.api_set)

    if not sources:
        answer = (
            "I couldn't find anything relevant in the indexed documentation for that "
            "question. Try rephrasing, or check that the relevant docs have been ingested."
        )
        if req.stream:

            def _empty():
                yield _sse({"type": "sources", "sources": [], "private_context": False})
                yield _sse({"type": "token", "text": answer})
                yield _sse({"type": "done"})

            return StreamingResponse(_empty(), media_type="text/event-stream")
        return {"answer": answer, "sources": [], "private_context": False}

    messages = prompts.build_messages(req.question, sources, settings.app_name)
    payload_sources = _sources_payload(sources)
    private_context = has_private_context(sources)

    if req.stream:

        def _gen():
            yield _sse(
                {
                    "type": "sources",
                    "sources": payload_sources,
                    "private_context": private_context,
                }
            )
            for token in llm.chat_stream(messages):
                yield _sse({"type": "token", "text": token})
            yield _sse({"type": "done"})

        return StreamingResponse(_gen(), media_type="text/event-stream")

    answer = llm.chat(messages)
    return {
        "answer": answer,
        "sources": payload_sources,
        "private_context": private_context,
    }


@app.post("/codegen")
def codegen(req: CodegenRequest):
    sources = retrieve(req.question, kb_id=req.kb_id, api_set=req.api_set)
    if not sources:
        return {
            "error": "No relevant documentation chunks were found.",
            "sources": [],
            "private_context": False,
        }

    private_context = has_private_context(sources)
    payload_sources = _sources_payload(sources)
    messages = prompts.build_codegen_messages(req.question, sources, settings.app_name)
    code_answer = llm.chat(messages)

    if private_context and settings.enable_private_code_encryption:
        if not req.recipient_public_key:
            raise HTTPException(
                status_code=400,
                detail="recipient_public_key is required when private context is used.",
            )
        encrypted = encrypt_payload(
            code_answer,
            recipient_public_key=req.recipient_public_key,
            key_id=settings.encryption_key_id,
        )
        return {
            "private_context": True,
            "sources": payload_sources,
            "provenance": [
                {
                    "n": s["n"],
                    "url": s["url"],
                    "visibility": s["visibility"],
                    "source_system": s["source_system"],
                }
                for s in payload_sources
            ],
            **encrypted,
        }

    return {
        "private_context": private_context,
        "sources": payload_sources,
        "code": code_answer,
    }


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


# ---- Static assets: widget + standalone page ----

@app.get("/widget.js")
def widget_js() -> FileResponse:
    return FileResponse(WEB_DIR / "widget.js", media_type="application/javascript")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html", media_type="text/html")

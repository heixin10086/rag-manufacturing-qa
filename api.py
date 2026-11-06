"""FastAPI 后端。给前端或其他系统调用。

启动：
    uvicorn api:app --reload --port 8000
接口文档：
    http://127.0.0.1:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import rag

app = FastAPI(title="制造企业诊断知识库问答 API", version="1.0.0")


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户问题")
    top_k: int = Field(5, ge=1, le=20, description="召回片段数")


class Hit(BaseModel):
    source: str
    chunk_id: str
    score: float


class AskResponse(BaseModel):
    answer: str
    hits: list[Hit]
    index_size: int


@app.get("/health")
def health() -> dict:
    try:
        size = rag.count()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok", "index_size": size}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    try:
        text, hits = rag.answer(req.query, top_k=req.top_k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AskResponse(
        answer=text,
        hits=[Hit(source=h["source"], chunk_id=h["chunk_id"], score=h["score"]) for h in hits],
        index_size=rag.count(),
    )

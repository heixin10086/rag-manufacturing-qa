"""RAG 核心链路：向量化 → 检索 → 拼装上下文 → 生成回答。

设计取舍：
- 不用 LangChain。链路总共不到 200 行，手写每一环都可解释，面试时说得清。
- embedding 与 chat 都走千问的 OpenAI 兼容接口，换供应商只需改 config。
- 回答强制带引用编号，便于核对，也用于抑制幻觉。
"""
from __future__ import annotations

import os
from functools import lru_cache

import chromadb
from openai import OpenAI

import config


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """千问（阿里云百炼）客户端。OpenAI 兼容协议，换 DeepSeek 只需改 base_url 与模型名。"""
    return OpenAI(
        api_key=config.require_api_key(),
        base_url=config.BASE_URL,
    )


@lru_cache(maxsize=1)
def get_collection():
    db = chromadb.PersistentClient(path=str(config.STORAGE_DIR))
    return db.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def count() -> int:
    return get_collection().count()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化。按 EMBED_BATCH_SIZE 切片，避免超过接口的单次条数上限。"""
    client = get_client()
    vectors: list[list[float]] = []
    size = max(1, config.EMBED_BATCH_SIZE)

    for i in range(0, len(texts), size):
        batch = texts[i : i + size]
        resp = client.embeddings.create(model=config.EMBED_MODEL, input=batch)
        # 接口不保证返回顺序，按 index 排序后再取
        vectors.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
        print(f"  已向量化 {min(i + size, len(texts))}/{len(texts)}")
    return vectors


def embed_query(query: str) -> list[float]:
    resp = get_client().embeddings.create(model=config.EMBED_MODEL, input=[query])
    return resp.data[0].embedding


def retrieve(query: str, top_k: int | None = None) -> list[dict]:
    """向量检索，返回带来源的片段列表。"""
    top_k = top_k or config.TOP_K
    collection = get_collection()
    if collection.count() == 0:
        raise RuntimeError("索引为空，请先运行 python ingest.py 构建索引。")

    result = collection.query(
        query_embeddings=[embed_query(query)],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits: list[dict] = []
    for text, meta, dist in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        hits.append(
            {
                "text": text,
                "source": (meta or {}).get("source", "unknown"),
                "chunk_id": (meta or {}).get("chunk_id", ""),
                "score": round(1 - float(dist), 4),  # cosine 距离转相似度，方便人看
            }
        )
    return hits


def build_context(hits: list[dict]) -> str:
    parts = []
    for i, hit in enumerate(hits, 1):
        parts.append(f"[{i}] 来源：{hit['source']}\n{hit['text']}")
    return "\n\n---\n\n".join(parts)


def answer(query: str, top_k: int | None = None, stream: bool = False):
    """返回 (回答文本, 命中片段)。stream=True 时返回生成器与命中片段。"""
    hits = retrieve(query, top_k)
    if not hits:
        return "资料中未找到相关内容。", []

    messages = [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"资料片段：\n\n{build_context(hits)}\n\n问题：{query}",
        },
    ]

    client = get_client()
    if stream:
        def gen():
            resp = client.chat.completions.create(
                model=config.CHAT_MODEL, messages=messages, stream=True
            )
            for chunk in resp:
                # 千问流式响应的最后一个 chunk 只带 usage，choices 是空数组。
                # 直接取 choices[0] 会抛 IndexError（页面表现为"list index out of range"）
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        return gen(), hits

    resp = client.chat.completions.create(model=config.CHAT_MODEL, messages=messages)
    return resp.choices[0].message.content, hits


if __name__ == "__main__":
    # 命令行快速自测：python rag.py "哪些企业已经上了 ERP 系统？"
    import sys

    q = " ".join(sys.argv[1:]) or "哪些企业已经上了 ERP 系统？"
    print(f"索引块数：{count()}")
    print(f"问题：{q}\n")
    text, hits = answer(q)
    print(text)
    print("\n--- 命中片段 ---")
    for i, h in enumerate(hits, 1):
        print(f"[{i}] {h['source']}  score={h['score']}  {h['text'][:60]}...")

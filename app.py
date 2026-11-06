"""Streamlit 前端（ModelScope 创空间 / Streamlit Cloud 的入口文件）。

本地运行：
    streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

import config
import rag

st.set_page_config(page_title="制造企业诊断知识库问答", page_icon="🔧", layout="wide")


@st.cache_resource(show_spinner=False)
def index_size() -> int:
    try:
        return rag.count()
    except Exception:
        return 0


st.title("制造企业智改数转 · 知识库问答")
st.caption(
    "基于企业诊断报告的检索增强问答（RAG）。回答仅依据知识库内容，并标注引用出处。"
    "语料已脱敏，企业名称以代号呈现。"
)

with st.sidebar:
    st.subheader("检索设置")
    top_k = st.slider("召回片段数 Top-K", 3, 10, config.TOP_K)
    st.caption(f"当前知识库：{index_size()} 个文本块")

    if st.button("清空对话", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption(f"生成模型：{config.CHAT_MODEL}")
    st.caption(f"向量模型：{config.EMBED_MODEL}")

if "messages" not in st.session_state:
    st.session_state.messages = []

# 回放历史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("hits"):
            with st.expander(f"引用来源（{len(msg['hits'])}）"):
                for i, hit in enumerate(msg["hits"], 1):
                    st.markdown(f"**[{i}] {hit['source']}** · 相似度 {hit['score']}")
                    st.caption(hit["text"][:500])

prompt = st.chat_input("例如：哪些企业已经上了 ERP 系统？")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            gen, hits = rag.answer(prompt, top_k=top_k, stream=True)
            # 流为空时 write_stream 返回 None，存进历史后回放会报错
            answer_text = st.write_stream(gen) or ""
        except Exception as exc:
            st.error(f"出错了：{exc}")
            st.stop()

        with st.expander(f"引用来源（{len(hits)}）", expanded=not hits):
            for i, hit in enumerate(hits, 1):
                st.markdown(f"**[{i}] {hit['source']}** · 相似度 {hit['score']}")
                st.caption(hit["text"][:500])

    st.session_state.messages.append(
        {"role": "assistant", "content": answer_text, "hits": hits}
    )

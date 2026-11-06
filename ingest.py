"""构建索引：解析 data/raw 下的报告 → 脱敏 → 按标题分块 → 向量化 → 写入 Chroma。

用法：
    python sanitize.py --suggest        # 先自动生成企业别名表
    python sanitize.py --check          # 确认没有漏网的企业名
    python ingest.py --dry-run          # 只分块不入库（不需要向量库和 API Key）
    python ingest.py                    # 建索引（已存在则追加）
    python ingest.py --rebuild          # 清空后重建（改过分块参数时用）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chunker import CLEAN_PATTERN, read_paragraphs, split_into_chunks
from config import CHUNK_OVERLAP, CHUNK_SIZE, COLLECTION_NAME, RAW_DIR, STORAGE_DIR
from sanitize import desensitize, load_alias


def collect_files(raw_dir: Path) -> list[Path]:
    files = sorted(set(list(raw_dir.rglob("*.docx")) + list(raw_dir.glob("*.docx"))))
    return [f for f in files if not f.name.startswith("~$")]  # 排除 Word 临时文件


def build_records(files: list[Path], alias: dict[str, str]) -> list[dict]:
    records: list[dict] = []
    for f in files:
        try:
            # 先脱敏、再分块：若先分块，企业名可能被块边界切断，
            # 留下一截无法匹配的企业名残片
            paras = read_paragraphs(f)
            paras = [(desensitize(text, alias), style) for text, style in paras]
            chunks = split_into_chunks(paras, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        except Exception as exc:
            print(f"[跳过] {f.name}: {exc}")
            continue

        kept = 0
        # 文件名同样含企业名，且会作为 source 拼进 prompt，必须一起脱敏
        safe_source = desensitize(f.stem, alias).strip()

        for i, chunk in enumerate(chunks):
            cleaned = CLEAN_PATTERN.sub(" ", desensitize(chunk, alias)).strip()
            if len(cleaned) < 120:  # 与 chunker.min_len 保持一致
                continue
            records.append({"id": f"{safe_source}-{i:04d}", "text": cleaned, "source": safe_source})
            kept += 1
        print(f"[解析] {safe_source} → {kept} 块")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="构建 RAG 索引")
    parser.add_argument("--rebuild", action="store_true", help="清空已有索引后重建")
    parser.add_argument("--dry-run", action="store_true", help="只分块不入库")
    args = parser.parse_args()

    if not RAW_DIR.exists():
        sys.exit(f"语料目录不存在：{RAW_DIR}\n请把脱敏前的报告 .docx 放进去。")

    files = collect_files(RAW_DIR)
    if not files:
        sys.exit(f"{RAW_DIR} 下没有找到 .docx 文件。")

    alias = load_alias()
    if not alias:
        print("提示：未找到企业别名表，本次不做企业名替换。建议先运行 python sanitize.py --suggest")

    records = build_records(files, alias)
    if not records:
        sys.exit("没有解析出任何有效文本，请检查报告格式。")

    total_chars = sum(len(r["text"]) for r in records)
    print(f"\n合计：{len(files)} 份报告，{len(records)} 个块，{total_chars:,} 字")
    print(f"平均块长：{total_chars // len(records)} 字 | 参数：size={CHUNK_SIZE} overlap={CHUNK_OVERLAP}")

    if args.dry_run:
        print("\n--- 抽样预览（前 3 块）---")
        for r in records[:3]:
            print(f"\n[{r['id']}] {r['text'][:240]}")
        return

    # 延迟导入：--dry-run 时不需要向量库与 API Key
    import chromadb

    import rag

    if args.rebuild:
        client = chromadb.PersistentClient(path=str(STORAGE_DIR))
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"已清空旧索引：{COLLECTION_NAME}")
        except Exception:
            print("未发现旧索引，直接新建。")

    collection = rag.get_collection()

    print("\n开始向量化……")
    vectors = rag.embed_texts([r["text"] for r in records])

    print("写入向量库……")
    batch = 500
    for i in range(0, len(records), batch):
        part = records[i : i + batch]
        collection.add(
            ids=[r["id"] for r in part],
            embeddings=vectors[i : i + batch],
            documents=[r["text"] for r in part],
            metadatas=[{"source": r["source"], "chunk_id": r["id"]} for r in part],
        )
        print(f"  已写入 {min(i + batch, len(records))}/{len(records)}")

    print(f"\n完成。当前索引块数：{rag.count()}")
    print('自测：python rag.py "哪些企业已经上了 ERP 系统？"')


if __name__ == "__main__":
    main()

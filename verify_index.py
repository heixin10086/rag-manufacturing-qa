"""交付前自检：确认索引里没有残留的真实企业名与联系方式。

对外投递简历或公开仓库时，语料必须脱敏。这个脚本直接扫向量库里的
正文和 metadata（source 也是企业名），比只检查原始 docx 更可靠。

用法：
    python verify_index.py
    python verify_index.py --alias data/company_alias.txt
"""
from __future__ import annotations

import argparse
import sys

from sanitize import COMPANY_PATTERN, EMAIL_PATTERN, PHONE_PATTERN, load_alias


def main() -> None:
    parser = argparse.ArgumentParser(description="索引脱敏自检")
    parser.add_argument("--alias", default=None, help="别名表路径")
    parser.add_argument("--sample", type=int, default=3, help="展示多少条命中样例")
    args = parser.parse_args()

    from pathlib import Path

    import rag

    alias_path = Path(args.alias) if args.alias else None
    alias = load_alias(alias_path) if alias_path else load_alias()

    collection = rag.get_collection()
    total = collection.count()
    if total == 0:
        sys.exit("索引为空，请先运行 ingest.py。")

    print(f"检查范围：{total} 个块（正文 + metadata）\n")

    data = collection.get(include=["documents", "metadatas"])
    hits: dict[str, list[str]] = {}
    contact = 0

    for doc, meta in zip(data["documents"], data["metadatas"]):
        text = doc or ""
        source = (meta or {}).get("source", "")

        # 已知企业名若还出现，说明映射没生效
        for real in alias:
            if real and real in text:
                hits.setdefault(real, []).append((meta or {}).get("chunk_id", "?"))
            if real and real in source:
                hits.setdefault(real, []).append(f"source:{source}")

        # 映射表之外的企业名（漏网）
        for name in COMPANY_PATTERN.findall(text):
            name = name.strip()
            if len(name) >= 4:
                hits.setdefault(name, []).append((meta or {}).get("chunk_id", "?"))

        contact += len(PHONE_PATTERN.findall(text)) + len(EMAIL_PATTERN.findall(text))

    if not hits and contact == 0:
        print("通过：索引内未发现真实企业名或联系方式。")
        print(f"（共校验 {len(alias)} 条已知企业名）")
        return

    print(f"未通过：发现 {len(hits)} 个疑似残留实体，{contact} 处联系方式。\n")
    for name, where in list(hits.items())[:12]:
        print(f"  {name}  出现在 {len(where)} 处，如 {where[0]}")
    if len(hits) > 12:
        print(f"  …… 还有 {len(hits) - 12} 个")

    print("\n处理方式：把缺失的企业名补进 data/company_alias.txt，然后：")
    print("  python ingest.py --rebuild && python verify_index.py")
    sys.exit(1)


if __name__ == "__main__":
    main()

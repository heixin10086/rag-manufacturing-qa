"""检索效果评测：这是整个项目最值钱的部分。

做法：自己出 N 个问题，标注「标准答案在哪份报告里」，然后看 Top-K 里有没有召回。
这比"感觉回答得挺好"有说服力得多，也正好对应数据分析岗要的评估能力。

用法：
    python eval.py                 # 默认跑 eval_set.json，Top-K = 5
    python eval.py --top-k 3
    python eval.py --show-miss     # 打印没命中的题目，便于调分块策略

评测集格式（data/eval_set.json）：
    [{"question": "问题原文", "expected_source": "报告的 file stem（不含 .docx）"}]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import config
import rag


def load_eval_set(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"评测集不存在：{path}\n请先按 README 的格式创建 data/eval_set.json。")

    data = json.loads(path.read_text(encoding="utf-8"))
    valid = [d for d in data if d.get("question") and d.get("expected_source")]
    if not valid:
        sys.exit("评测集里没有有效条目，检查 question 与 expected_source 字段。")
    return valid


def main() -> None:
    parser = argparse.ArgumentParser(description="检索命中率评测")
    parser.add_argument("--top-k", type=int, default=config.TOP_K)
    parser.add_argument("--show-miss", action="store_true", help="打印未命中的题目")
    parser.add_argument("--out", type=str, default="", help="把结果保存为 JSON")
    args = parser.parse_args()

    cases = load_eval_set(config.EVAL_FILE)
    print(f"评测集：{len(cases)} 题 | 索引块数：{rag.count()} | Top-K：{args.top_k}\n")

    hits_at_k = 0
    misses: list[dict] = []
    rows: list[dict] = []

    for i, case in enumerate(cases, 1):
        q = case["question"]
        expected = case["expected_source"].strip()
        try:
            hits = rag.retrieve(q, top_k=args.top_k)
        except Exception as exc:
            print(f"[{i:02d}] 检索失败：{exc}")
            continue

        sources = [h["source"] for h in hits]
        hit = expected in sources
        rank = sources.index(expected) + 1 if hit else None
        hits_at_k += int(hit)

        rows.append(
            {
                "question": q,
                "expected": expected,
                "hit": hit,
                "rank": rank,
                "top_sources": sources,
            }
        )

        mark = f"命中 rank={rank}" if hit else "未命中"
        print(f"[{i:02d}] {mark:12s} | {q[:34]}")
        if not hit:
            misses.append(rows[-1])

    total = len(rows)
    if total == 0:
        sys.exit("没有完成任何评测，检查知识库是否已建立。")

    rate = hits_at_k / total
    print(f"\n{'=' * 46}")
    print(f"检索命中率 Hit@{args.top_k}：{hits_at_k}/{total} = {rate:.1%}")
    print(f"{'=' * 46}")

    if args.show_miss and misses:
        print("\n未命中明细：")
        for m in misses:
            print(f"\n  问题：{m['question']}")
            print(f"  期望：{m['expected']}")
            print(f"  实召回：{', '.join(m['top_sources'])}")
        print("\n排查方向：调 CHUNK_SIZE、加大小重叠、或引入 reranker 重排。")

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(
            json.dumps(
                {"top_k": args.top_k, "hit_rate": rate, "cases": rows},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\n结果已保存：{out_path}")


if __name__ == "__main__":
    main()

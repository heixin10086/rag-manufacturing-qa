"""分块与解析：把 docx 报告切成适合检索的文本块。

单独成模块的原因：这层逻辑不依赖向量库和 API，可以离线单测。
分块质量直接决定检索效果，是整个 RAG 里最值得反复调的一环。

两条经验（针对企业诊断报告这类模板化公文）：
1. 只在一级标题处切块。「（一）（二）」这类二级标题留在块内，
   否则每块只有 200 字，语义不完整，检索时还容易把上下文切断。
2. 必须过滤模板套话。每份报告开头的「报告要求 / 正文使用三号仿宋 /
   页边距 3.2 厘米」都是格式说明，不是知识，会挤占 Top-K 名额。
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

# 一级标题：这些才作为切块边界
MAJOR_PREFIXES = (
    "一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、", "九、", "十、",
    "十一、", "十二、",
)

# 模板套话：报告中固定出现的格式说明或封面要素，一律丢弃
NOISE_PATTERNS = (
    "需盖章",
    "报告要求",
    "正文使用三号",
    "行间距设置",
    "页边距：",
    "页码使用",
    "首行缩进",
    "诊断报告编制日期",
    "诊 断 专 家",
    "诊 断 服 务",
    "诊 断 机 构",
    "本报告仅用于",
    "模板",
)

# 连续的不可见空白压成一个空格，但保留换行
CLEAN_PATTERN = re.compile(r"[ \t\u3000]+")


def is_noise(text: str) -> bool:
    """判断是否为模板套话/封面要素。"""
    return any(p in text for p in NOISE_PATTERNS)


def is_heading(text: str, style_name: str = "") -> bool:
    """判断是否为一级标题（切块边界）。二级标题（一）（二）不切。"""
    if style_name and style_name.lower() in ("heading 1", "标题 1"):
        return True
    t = text.strip()
    return 0 < len(t) <= 40 and t.startswith(MAJOR_PREFIXES)


def _table_lines(table: Table) -> list[str]:
    """把表格按行拍成 "单元格 | 单元格" 的文本行。

    基本信息表、指标评分表都是有效信息，必须保留；
    合并单元格会让同一文本重复出现，用 dict.fromkeys 去重。
    """
    lines: list[str] = []
    for row in table.rows:
        cells = [c.text.strip().replace("\n", " ") for c in row.cells if c.text and c.text.strip()]
        if not cells:
            continue
        line = " | ".join(dict.fromkeys(cells))
        if len(line) >= 4 and not is_noise(line):
            lines.append(line)
    return lines


def read_paragraphs(path: Path) -> list[tuple[str, str]]:
    """按文档原始顺序返回 [(文本, 样式名)]，段落与表格混排。

    早期版本先取全部段落、再追加全部表格，会把表格内容挤到文末，
    导致「（一）企业基本信息表」后面接不到表里的数据 —— 顺序必须保留。
    """
    doc = Document(str(path))
    out: list[tuple[str, str]] = []

    # python-docx 1.1+ 提供按正文顺序迭代段落与表格的接口
    if hasattr(doc, "iter_inner_content"):
        items = doc.iter_inner_content()
    else:  # 老版本降级：先段落后表格，顺序会失真但不会崩
        items = list(doc.paragraphs) + list(doc.tables)

    for item in items:
        if isinstance(item, Table):
            out.extend((line, "") for line in _table_lines(item))
            continue
        if isinstance(item, Paragraph):
            text = item.text.strip()
            if not text or is_noise(text):
                continue
            style = item.style.name if item.style else ""
            out.append((text, style))

    return out


def _find_cut(buf: str, size: int, floor_ratio: float = 0.6) -> int:
    """在 [size*floor_ratio, size] 区间内找最靠后的句末标点，作为切分位置。

    纯按字符数切会把结论句劈成两半（"……无法支撑批次级" | "分析。"），
    检索时两边都缺信息。优先在句号/分号/换行处断开，能让每块语义完整。
    """
    floor = int(size * floor_ratio)
    best = -1
    for sep in ("\n", "。", "；", "！", "？", "，", "、"):
        idx = buf.rfind(sep, floor, size)
        if idx > best:
            best = idx
    return best + 1 if best >= floor else size


def split_into_chunks(
    paras: list[tuple[str, str]],
    size: int = 320,
    overlap: int = 60,
    min_len: int = 120,
) -> list[str]:
    """按一级标题切块，块内再按长度二次切分。

    size: 目标块长（字符）
    overlap: 相邻块的重叠长度，避免结论句被边界切断
    min_len: 小于该长度的碎片直接丢弃（页眉页脚、孤立短句）
    """
    if overlap >= size:
        raise ValueError("overlap 必须小于 size，否则会死循环")

    chunks: list[str] = []
    buf = ""

    for text, style in paras:
        if is_heading(text, style) and buf.strip():
            chunks.append(buf.strip())
            buf = text + "\n"
            continue

        buf += text + "\n"

        while len(buf) >= size:
            cut = _find_cut(buf, size)
            chunks.append(buf[:cut].strip())
            buf = buf[max(0, cut - overlap) :]

    if buf.strip():
        chunks.append(buf.strip())

    return [c for c in chunks if len(c) >= min_len]


def chunk_file(path: Path, size: int = 320, overlap: int = 60, min_len: int = 120) -> list[str]:
    return split_into_chunks(read_paragraphs(path), size=size, overlap=overlap, min_len=min_len)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法：python chunker.py <报告.docx> [块长] [重叠]")
        sys.exit(1)

    p = Path(sys.argv[1])
    s = int(sys.argv[2]) if len(sys.argv) > 2 else 320
    o = int(sys.argv[3]) if len(sys.argv) > 3 else 60

    chunks = chunk_file(p, s, o)
    print(f"文件：{p.name}")
    print(f"块数：{len(chunks)} | 平均长度：{sum(map(len, chunks)) // max(1, len(chunks))} 字")
    for i, c in enumerate(chunks[:4], 1):
        print(f"\n--- 第 {i} 块（{len(c)} 字）---")
        print(c[:260])

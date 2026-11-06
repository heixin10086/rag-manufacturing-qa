"""脱敏：把企业名称换成代号，清理电话/邮箱/身份证等敏感信息。

用法：
    python sanitize.py --suggest     # 扫描 data/raw 下的报告，自动生成别名表草稿
    python sanitize.py --check       # 检查语料里还残留哪些敏感信息

企业诊断报告属于企业内部分析材料，对外投递简历 / 公开仓库前必须脱敏。
"""
import argparse
import json
import re
import sys
from pathlib import Path

from config import ALIAS_FILE, RAW_DIR

# 企业名候选：以公司/研究院结尾的中文实体名
# 注意不含单独的「集团」——正文里「售后由集团统一管理」会被误匹配成企业名
COMPANY_PATTERN = re.compile(
    r"[\u4e00-\u9fa5A-Za-z（）()]{2,24}?"
    r"(?:股份有限公司|有限责任公司|有限公司|研究院|研究所)"
)

# 常见敏感信息
PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
ID_PATTERN = re.compile(r"\d{17}[\dXx]")

# 轻量噪声词：避免把格式说明、模板名当成企业名
_NOISE_WORDS = ("需盖章", "报告要求", "正文使用", "行间距", "页边距", "页码", "填写版", "模板")


def is_noise(text: str) -> bool:
    return any(w in text for w in _NOISE_WORDS)


def load_alias(path: Path = ALIAS_FILE) -> dict[str, str]:
    """读取别名表。每行格式：原名|代号，忽略空行与 # 注释。

    行尾的行内注释（`原名|企业A  # 出现 6 次`）会被剥离——
    否则代号会变成 "企业A  # 出现 6 次" 一起写进语料。
    """
    mapping: dict[str, str] = {}
    if not path.exists():
        return mapping
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()  # 先剥行内注释
        if not line or "|" not in line:
            continue
        real, alias = (s.strip() for s in line.split("|", 1))
        if real and alias:
            mapping[real] = alias
    return mapping


def desensitize(text: str, mapping: dict[str, str]) -> str:
    """替换企业名并清理联系方式。按名称长度倒序替换，避免短名先命中长名的一部分。"""
    for real in sorted(mapping, key=len, reverse=True):
        text = text.replace(real, mapping[real])
    text = PHONE_PATTERN.sub("[电话]", text)
    text = EMAIL_PATTERN.sub("[邮箱]", text)
    text = ID_PATTERN.sub("[证件号]", text)
    return text


def suggest_alias(raw_dir: Path = RAW_DIR, out_path: Path = ALIAS_FILE) -> None:
    """生成企业别名表草稿。

    提取顺序很重要：
    1. 先从**文件名**取主体企业（「企业名-智改数转诊断报告.docx」），这最可靠；
    2. 再从正文补充其他提到的公司（客户、供应商），这些需要人工确认。
    早期版本只从正文正则提取，抓进了「民营企业（集团」这类片段，
    又漏掉了文件名里的真实企业，导致脱敏失效。
    """
    if not raw_dir.exists():
        sys.exit(f"目录不存在：{raw_dir}")

    main_names: dict[str, int] = {}
    other_names: dict[str, int] = {}

    files = sorted(set(list(raw_dir.rglob("*.docx")) + list(raw_dir.glob("*.docx"))))
    for f in files:
        # 1) 文件名中的主体企业
        main = f.stem.split("-")[0].strip()
        main = re.sub(r"[（(]填写版[)）]", "", main).strip()
        if len(main) >= 4 and not is_noise(main):
            main_names[main] = main_names.get(main, 0) + 1

        # 2) 正文中的其他企业
        try:
            from docx import Document

            doc = Document(str(f))
            content = "\n".join(p.text for p in doc.paragraphs)
        except Exception as exc:
            print(f"[跳过] {f.name}: {exc}")
            continue
        for name in COMPANY_PATTERN.findall(content):
            name = name.strip()
            if len(name) >= 6 and name not in main_names and not is_noise(name):
                other_names[name] = other_names.get(name, 0) + 1

    if not main_names and not other_names:
        sys.exit("没有提取到任何企业名，请检查 data/raw 下的文件命名。")

    lines = [
        "# 企业名脱敏映射表：原名|代号",
        "# 前段为文件名中的主体企业（可靠），后段为正文提及的其他公司（需人工核对）",
        "# 代号一旦确定不要改，改名会导致已有索引与来源标注不一致",
        "",
        "# ---- 主体企业 ----",
    ]

    def gen_alias(i: int) -> str:
        """生成 企业A..企业Z, 企业AA..，避免超过 26 家后乱序"""
        if i < 26:
            return f"企业{chr(65 + i)}"
        return f"企业{chr(65 + i // 26 - 1)}{chr(65 + i % 26)}"

    idx = 0
    for name, freq in sorted(main_names.items(), key=lambda x: -x[1]):
        lines.append(f"{name}|{gen_alias(idx)}  # 主体企业，出现 {freq} 份报告")
        idx += 1

    if other_names:
        lines.append("")
        lines.append("# ---- 正文提及的其他公司（请人工确认是否需要）----")
        for j, (name, freq) in enumerate(sorted(other_names.items(), key=lambda x: -x[1])):
            lines.append(f"{name}|其他公司{j + 1}  # 出现 {freq} 次")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"已生成 {out_path}")
    print(f"  主体企业 {len(main_names)} 家（来自文件名，可信）")
    print(f"  其他公司 {len(other_names)} 个（来自正文，建议抽检）")


def check(raw_dir: Path = RAW_DIR, alias_path: Path = ALIAS_FILE) -> None:
    """检查语料中残留的未脱敏企业名与联系方式。"""
    mapping = load_alias(alias_path)
    files = list(raw_dir.rglob("*.docx")) + list(raw_dir.glob("*.docx"))
    leftovers: dict[str, int] = {}
    contact = 0

    for f in set(files):
        try:
            from docx import Document

            doc = Document(str(f))
            content = "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            continue
        for name in COMPANY_PATTERN.findall(content):
            name = name.strip()
            if len(name) >= 4 and name not in mapping:
                leftovers[name] = leftovers.get(name, 0) + 1
        contact += len(PHONE_PATTERN.findall(content)) + len(EMAIL_PATTERN.findall(content))

    if not leftovers and contact == 0:
        print("检查通过：未发现未映射的企业名或联系方式。")
        return

    print(f"发现 {len(leftovers)} 个未映射的企业名，{contact} 处联系方式：")
    for name, freq in sorted(leftovers.items(), key=lambda x: -x[1])[:30]:
        print(f"  {name}  ({freq})")
    print("\n请补充到 data/company_alias.txt 后重新执行 ingest。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="语料脱敏工具")
    parser.add_argument("--suggest", action="store_true", help="自动生成企业别名表草稿")
    parser.add_argument("--check", action="store_true", help="检查残留敏感信息")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出映射表")
    args = parser.parse_args()

    if args.suggest:
        suggest_alias()
    elif args.check:
        check()
    elif args.json:
        print(json.dumps(load_alias(), ensure_ascii=False, indent=2))
    else:
        parser.print_help()

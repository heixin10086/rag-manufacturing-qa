"""生成 3 份**完全虚构**的示例诊断报告，用于公开仓库演示。

为什么需要这个：
    真实的 43 份企业诊断报告属于实习单位的工作成果，含企业敏感信息，
    不能进公开仓库。但仓库如果只有代码、没有数据，别人 clone 下来跑不起来。
    所以准备一份虚构语料，结构和真实报告一致，内容全部凭空编造。

用法：
    python scripts/make_samples.py
输出：
    data/samples/*.docx
"""
from __future__ import annotations

from pathlib import Path

from docx import Document

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"

SAMPLES = [
    {
        "name": "星海精密仪器（宁波）有限公司",
        "industry": "电子信息/仪器仪表",
        "employees": "约 120 人",
        "revenue": "约 6,800 万元",
        "scale": "小型企业",
        "overall": (
            "该公司主营环境监测类精密仪器的研发与制造，产品以温湿度记录仪、"
            "气体检测仪为主，内销与出口各占约一半。生产以多品种小批量为主，"
            "装配环节人工占比高。企业已通过高新技术企业认定，拥有 14 项实用新型专利。"
        ),
        "systems": (
            "企业已部署金蝶云星空 ERP，覆盖采购、销售、库存、财务模块，"
            "2023 年上线，云端部署；生产现场未部署 MES，车间报工仍以纸质流转单为主；"
            "研发部门使用 SolidWorks 进行三维设计，但图纸版本管理依赖共享文件夹；"
            "质量检验使用 Excel 记录，未接入系统。"
        ),
        "problems": [
            "生产进度不透明：车间在制品状态无法实时掌握，订单交期承诺依赖计划员经验估计。",
            "质量数据分散：检验记录以 Excel 和纸质表单保存，出现客诉时追溯耗时超过 4 小时。",
            "设备管理粗放：关键校准设备的校准周期靠人工台账提醒，曾出现超期使用情况。",
            "研发协同效率低：图纸版本混乱，同一零件存在多个版本并存的情况。",
        ],
        "advice": [
            "优先上线轻量级 MES，先打通报工与质量追溯两个最小闭环，预计投入 30 万元以内。",
            "将检验记录电子化，与 ERP 的批次信息关联，实现扫码追溯。",
            "建立设备台账系统，设置校准到期自动提醒。",
            "引入图文档管理系统（PDM），先解决版本管理，再考虑与设计工具集成。",
        ],
    },
    {
        "name": "朗岳自动化装备（合肥）有限公司",
        "industry": "汽车/机械/制造",
        "employees": "约 260 人",
        "revenue": "约 1.6 亿元",
        "scale": "中型企业",
        "overall": (
            "该公司为非标自动化产线的设计与集成商，主要服务新能源与家电行业客户。"
            "项目制生产特征明显，单个项目周期 3 至 9 个月，设计工作量占比高。"
            "近三年营收年均增长约 20%，但人均产值增长停滞。"
        ),
        "systems": (
            "企业自研了一套项目管理系统，覆盖立项、设计、采购、装配、调试节点；"
            "ERP 采用用友 U8，与项目系统通过中间表每日同步一次；"
            "设计端全面使用 SolidWorks 与 EPLAN，已实施 PDM，版本受控；"
            "生产现场有 6 台数控设备，均未联网，程序通过 U 盘传输。"
        ),
        "problems": [
            "两套系统数据不同步：项目系统与 ERP 每日同步一次，导致采购缺料预警滞后一天。",
            "数控设备未联网：加工程序靠人工拷贝，存在错用旧版程序的风险，且无法统计设备稼动率。",
            "项目成本核算滞后：项目实际成本要等项目结束后才能归集，过程中无法预警超支。",
            "知识沉淀不足：调试经验集中在少数几位老师傅身上，新人上手周期长。",
        ],
        "advice": [
            "打通项目系统与 ERP 的实时接口，把缺料预警提前到当日。",
            "先对 6 台数控设备做联网改造（DNC），解决程序版本与稼动率统计问题。",
            "建立项目级成本看板，按里程碑归集实际成本，设置超支阈值预警。",
            "把调试经验整理成标准化作业包（SOP + 故障案例库），配合内部培训。",
        ],
    },
    {
        "name": "宁泰电气设备（常州）有限公司",
        "industry": "电子/通信/硬件",
        "employees": "约 85 人",
        "revenue": "约 4,300 万元",
        "scale": "小型企业",
        "overall": (
            "该公司生产低压配电柜与控制柜，以按单设计、按单生产为主，"
            "客户集中在长三角地区的建筑与工业厂房项目。"
            "企业规模不大，但订单稳定，近两年开始承接部分海外项目。"
        ),
        "systems": (
            "企业尚未部署完整 ERP，仅使用一套进销存软件管理库存与开票；"
            "设计与报价依赖 CAD 与 Excel，重复设计工作量大；"
            "车间无任何信息化系统，生产靠班组长口头安排；"
            "已使用企业微信做内部沟通，但未与业务系统打通。"
        ),
        "problems": [
            "报价依赖人工：相似柜型的报价需要重新核算，平均耗时 2 天，影响响应速度。",
            "设计复用率低：缺乏标准柜型库，同类项目重复设计，设计工时占比过高。",
            "库存账实不符：进销存软件只记录出入库单据，未与车间领料联动，盘点差异率约 8%。",
            "生产进度靠问：客户催单时需电话询问班组长，无法给出准确交期。",
        ],
        "advice": [
            "先建标准柜型库与参数化报价模板，把常见柜型的报价压缩到 2 小时内。",
            "上线轻量 ERP 的库存与生产模块，实现领料与库存联动，先把账实差异降到 3% 以内。",
            "车间设置简易报工终端（平板或扫码枪），解决进度可见性。",
            "暂不建议上 MES，当前订单复杂度与管理基础尚不足以支撑。",
        ],
    },
]


def build_report(sample: dict, out_dir: Path) -> Path:
    doc = Document()
    doc.add_heading(sample["name"], level=0)

    doc.add_heading("一、企业基本情况", level=1)
    doc.add_heading("（一）企业基本信息表", level=2)
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for k, v in [
        ("企业名称", sample["name"]),
        ("所属行业", sample["industry"]),
        ("职工人数", sample["employees"]),
        ("上年度主营业务收入", sample["revenue"]),
        ("企业规模", sample["scale"]),
    ]:
        row = table.add_row().cells
        row[0].text = k
        row[1].text = v

    doc.add_heading("（二）企业总体情况", level=2)
    doc.add_paragraph(sample["overall"])

    doc.add_heading("二、数字化现状评估", level=1)
    doc.add_paragraph(sample["systems"])

    doc.add_heading("三、存在的主要问题", level=1)
    for i, p in enumerate(sample["problems"], 1):
        doc.add_paragraph(f"{i}. {p}")

    doc.add_heading("四、改造建议", level=1)
    for i, a in enumerate(sample["advice"], 1):
        doc.add_paragraph(f"{i}. {a}")

    doc.add_heading("五、说明", level=1)
    doc.add_paragraph(
        "本报告为公开仓库演示用的虚构样例，企业名称、人员规模、营收数据、"
        "系统现状与问题描述均为编造，不对应任何真实企业。"
    )

    path = out_dir / f"{sample['name']}-智改数转诊断报告（示例）.docx"
    doc.save(str(path))
    return path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for s in SAMPLES:
        p = build_report(s, OUT_DIR)
        print(f"已生成 {p.name}  ({p.stat().st_size // 1024} KB)")
    print(f"\n共 {len(SAMPLES)} 份虚构样例，位于 {OUT_DIR}")
    print("演示时：把这些复制到 data/raw/ 再建索引即可（真实语料请勿提交到仓库）")


if __name__ == "__main__":
    main()

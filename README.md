# 制造企业智改数转 · 知识库问答（RAG）

把 40 余份企业智改数转诊断报告变成可检索的知识库，用自然语言提问并给出带出处的回答。

> 起因：实习时参与过制造企业的数字化转型诊断项目，报告一多，想查"哪类企业普遍上了 ERP""某类企业的瓶颈集中在哪个环节"就得一份份翻。于是做了这个检索增强问答系统。

## 技术链路

```
docx 报告
   │  python-docx 解析
   ▼
按标题分块（320 字/块，60 字重叠）
   │  企业名脱敏
   ▼
text-embedding-v3 向量化
   │
   ▼
Chroma 持久化（cosine 相似度）
   │  查询时召回 Top-5
   ▼
qwen3.8-flash 生成（强制标注引用编号）
   │
   ▼
Streamlit 前端 / FastAPI 接口
```

**设计取舍**：不用 LangChain。整条链路不到 200 行，每一环都可控可解释；面试时能讲清楚为什么这样分块、为什么带引用。

## 目录

```
├── config.py           # 模型、分块、检索参数（全部可由环境变量覆盖）
├── sanitize.py         # 脱敏：企业名换代号、清理电话邮箱
├── ingest.py           # 建索引：解析 → 脱敏 → 分块 → 向量化 → 入库
├── rag.py              # 检索 + 生成（核心链路）
├── app.py              # Streamlit 前端（创空间入口）
├── api.py              # FastAPI 接口
├── eval.py             # 检索命中率评测
├── data/
│   ├── raw/            # 原始报告 .docx（不入 git）
│   ├── company_alias.txt  # 企业名 → 代号
│   └── eval_set.json   # 评测集
└── storage/            # Chroma 持久化（不入 git）
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置密钥
cp .env.example .env      # 填入 DASHSCOPE_API_KEY

# 3. 放入语料
#    把诊断报告 .docx 放进 data/raw/

# 4. 生成脱敏映射表，人工核对
python sanitize.py --suggest
python sanitize.py --check     # 确认没有漏网的企业名

# 5. 建索引
python ingest.py --dry-run     # 先看切块效果
python ingest.py --rebuild     # 正式建库

# 6. 自测
python rag.py "哪些企业已经上了 ERP 系统？"

# 7. 起界面
streamlit run app.py
```

## 关于数据（重要）

**本仓库不包含任何真实企业语料。**

真实的 40 余份企业诊断报告是实习期间的工作成果，含企业经营数据与系统架构等敏感信息，
即使做企业名替换也可能被反推识别，因此不适合公开：

- `data/raw/`、`data/company_alias.txt`、`storage/` 均已加入 `.gitignore`
- 仓库提供 3 份**完全虚构**的示例报告（`data/samples/`），结构与真实报告一致，内容凭空编造

想跑通流程：

```bash
python scripts/make_samples.py            # 生成虚构样例
cp data/samples/*.docx data/raw/          # Windows: copy data\samples\*.docx data\raw\
python ingest.py --rebuild
streamlit run app.py
```

**真实语料下的实测规模**（仅规模，不含内容）：43 份报告 → 678 个检索块，
约 20 万字，平均块长 296 字，全量向量化约 2 分钟。

## 评测

自己出 20 个问题，标注标准答案所在的报告文件名，填进 `data/eval_set.json`：

```json
[{"question": "哪些企业已部署 ERP？", "expected_source": "企业A-智改数转诊断报告"}]
```

```bash
python eval.py --top-k 5 --show-miss
```

输出 `Hit@5` 命中率。建议做两组对比写进 README：

| 配置 | Hit@5 |
|---|---|
| 纯向量检索（chunk=320, overlap=60） | 待填 |
| 调整分块 + 加大重叠 | 待填 |
| 加 reranker 重排（bge-reranker-v2-m3） | 待填 |

## 部署到 ModelScope 创空间

1. `modelscope.cn` 注册 → 创建创空间 → SDK 选 **Streamlit**
2. 上传代码（`app.py` 为入口），**不要上传** `data/raw/` 与 `storage/`
3. 在创空间设置里添加环境变量 `DASHSCOPE_API_KEY`
4. 注意：创空间实例不会自动建索引，需先在本地建好再上传 `storage/`，或启动脚本里判断为空时建库

## 已知限制

- 单轮问答，没有做对话历史压缩，多轮追问能力有限
- 分块按标题切，对没有小标题的报告效果会打折
- 未做 rerank 时，长文档的相似片段容易挤掉真正相关的那一块

## 后续可做

- 混合检索（BM25 + 向量）提升专有名词召回
- 引入 bge-reranker 做二阶段重排
- 答案结构化输出（把"企业 + 环节 + 问题"抽成表格）

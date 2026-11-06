"""全局配置：路径、模型、分块与检索参数。

所有密钥从环境变量读取，禁止硬编码。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"                  # 放脱敏前的 .docx 原始报告
ALIAS_FILE = DATA_DIR / "company_alias.txt"  # 企业名 → 代号的映射表
EVAL_FILE = DATA_DIR / "eval_set.json"       # 评测集
STORAGE_DIR = BASE_DIR / "storage"           # 向量库持久化目录

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# 注意：数据目录不在 git 中，克隆后需要自行补齐

# 模型配置（千问 / 阿里云百炼，OpenAI 兼容接口）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen-plus")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-v3")

# 单次 embedding 请求的文本条数。百炼对 input 数组有条数上限，10 是安全值
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "10"))

# 向量库
COLLECTION_NAME = os.getenv("COLLECTION", "diag_kb")

# 分块参数（中文报告按 320 字一块，60 字重叠，避免结论被切断）
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "320"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "60"))

# 检索参数
TOP_K = int(os.getenv("TOP_K", "5"))

SYSTEM_PROMPT = (
    "你是一名制造业数字化转型顾问助手。请严格依据给定的资料片段回答问题。\n"
    "规则：\n"
    "1. 只使用资料中的信息，不要引入外部知识；\n"
    "2. 资料中没有的内容，直接回答「资料中未提及」，不要猜测；\n"
    "3. 回答末尾用 [编号] 标注引用的资料片段，如 [1][3]；\n"
    "4. 用简洁的中文回答，必要时分点陈述。"
)


def require_api_key() -> str:
    """取 API Key，缺失时给出明确提示而不是抛 KeyError。"""
    if not DASHSCOPE_API_KEY or DASHSCOPE_API_KEY.startswith("sk-xxxx"):
        raise RuntimeError(
            "未配置 DASHSCOPE_API_KEY。请复制 .env.example 为 .env，填入阿里云百炼的 API Key。"
        )
    return DASHSCOPE_API_KEY

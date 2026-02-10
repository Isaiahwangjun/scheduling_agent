"""
LLM 設定 - 統一管理 LLM 實例
"""

import os
from langchain_openai import ChatOpenAI


def get_llm(temperature: float = 0) -> ChatOpenAI:
    """取得 LLM 實例"""
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "claude-4.5-opus-aws"),
        temperature=temperature,
        base_url=os.getenv("OPENAI_API_BASE"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )

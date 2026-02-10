"""
最終處理節點
MCP 操作已在 meeting_agent 中由 LLM 自主執行
"""

import logging
from ..state import AgentState

logger = logging.getLogger("agent")


def finalize(state: AgentState) -> dict:
    """最終處理"""
    email_id = state["email"]["id"]
    category = state.get("category", "?")

    logger.info(f"[Finalize] 完成 {email_id}: {category}")
    logger.info("")  # 空行分隔

    return {}

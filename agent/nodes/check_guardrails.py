"""
護欄檢查節點 - 檢查回覆內容，防止未授權的金錢/合約承諾
"""

import logging
from typing import Literal
from langgraph.types import Command

from ..state import AgentState

logger = logging.getLogger("agent")

# 敏感關鍵詞
SENSITIVE_KEYWORDS = [
    "報價",
    "價格",
    "費用",
    "合約",
    "簽約",
    "付款",
    "訂金",
    "定金",
    "折扣",
    "優惠價",
]


def check_guardrails(state: AgentState) -> Command[Literal["finalize"]]:
    """檢查護欄 - 審核回覆內容"""
    category = state.get("category", "")
    reply = state.get("reply", "")

    logger.info(f"[Guardrails] 檢查護欄...")

    triggered = False
    reason = None

    # 規則 1: 詢價郵件需人工審核
    if category == "詢價":
        triggered = True
        reason = "詢價郵件 - 回覆內容需人工確認"

    # 規則 2: 檢查回覆中是否包含敏感關鍵詞
    if not triggered and reply:
        for keyword in SENSITIVE_KEYWORDS:
            if keyword in reply:
                triggered = True
                reason = f"回覆包含敏感關鍵詞「{keyword}」- 可能涉及金錢/合約承諾"
                break

    if triggered:
        logger.info(f"[Guardrails] ⚠️ 觸發: {reason}")
    else:
        logger.info(f"[Guardrails] ✓ 通過")

    return Command(
        update={
            "guardrail_triggered": triggered,
            "guardrail_reason": reason,
            "needs_human_review": triggered,
        },
        goto="finalize",
    )

"""
分類節點 - 郵件分類 + 優先級
"""

import logging
from typing import Literal
from langgraph.types import Command
from pydantic import BaseModel, Field

from ..state import AgentState
from ..llm import get_llm

logger = logging.getLogger("agent")


class ClassificationResult(BaseModel):
    """分類結果"""

    category: Literal["急件", "一般", "詢價", "會議邀約", "垃圾"] = Field(
        description="郵件分類"
    )
    priority: int = Field(ge=1, le=5, description="優先級 1-5，5 最高")
    reasoning: str = Field(description="分類理由")


CLASSIFY_PROMPT = """你是一個郵件分類助理。請分析以下郵件並分類。

## 分類規則
- 急件：老闆/主管發的、標題含「緊急」、當日截止
- 會議邀約：邀請開會、約時間討論、改期請求
- 詢價：詢問產品價格、報價
- 垃圾：行銷廣告、Newsletter、促銷
- 一般：其他（帳單、收據、通知等）

## 優先級規則 (1-5，5 最高)
- 5: 老闆發的急件、當日截止
- 4: 重要會議邀約、合作夥伴
- 3: 一般會議、詢價
- 2: 內部通知、一般郵件
- 1: Newsletter、收據、垃圾

## 郵件
寄件者: {sender}
主題: {subject}
時間: {timestamp}
內容: {content}
"""


def classify(state: AgentState) -> Command[Literal["meeting_agent", "generate_reply", "finalize"]]:
    """分類郵件，並根據結果路由"""
    email = state["email"]

    logger.info(f"[Classify] 分類郵件: {email['subject']}")

    llm = get_llm()
    structured_llm = llm.with_structured_output(ClassificationResult)

    prompt = CLASSIFY_PROMPT.format(
        sender=email["sender"],
        subject=email["subject"],
        timestamp=email["timestamp"],
        content=email["content"],
    )

    result: ClassificationResult = structured_llm.invoke(prompt)

    logger.info(f"[Classify] 結果: {result.category} (優先級 {result.priority})")
    logger.info(f"[Classify] 理由: {result.reasoning}")

    # 路由決策
    if result.category == "會議邀約":
        next_node = "meeting_agent"
    elif result.category == "垃圾":
        next_node = "finalize"  # 垃圾郵件直接結束，不需回覆
    else:
        next_node = "generate_reply"

    logger.info(f"[Classify] 下一步: {next_node}")

    return Command(
        update={
            "category": result.category,
            "priority": result.priority,
            "reasoning": result.reasoning,
        },
        goto=next_node,
    )

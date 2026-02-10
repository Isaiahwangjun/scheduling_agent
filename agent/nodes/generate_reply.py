"""
回覆生成節點 - 根據分析結果生成回覆
"""

import logging
from typing import Literal
from langgraph.types import Command
from pydantic import BaseModel, Field

from ..state import AgentState
from ..llm import get_llm

logger = logging.getLogger("agent")


class ReplyResult(BaseModel):
    """回覆結果"""

    needs_reply: bool = Field(description="是否需要回覆")
    reply: str | None = Field(default=None, description="回覆內容")


REPLY_PROMPT = """你是一個郵件回覆助理。請根據以下資訊生成適當的回覆。

## 郵件資訊
寄件者: {sender}
主題: {subject}
內容: {content}

## 分類結果
分類: {category}
優先級: {priority}

## 會議資訊
{meeting_info}

## 行事曆檢查結果
是否為工作日: {is_working_day}
非工作日原因: {non_working_reason}
是否有衝突: {has_conflict}
衝突事件: {conflict_with}
建議日期: {suggested_dates}

## 回覆規則
1. 垃圾郵件：不回覆
2. 一般郵件（收據、帳單等）：不回覆
3. 詢價郵件：只能確認收到，不能報價，告知會有專人回覆
4. 會議邀約：
   - 若日期是非工作日（週末/假日）：婉拒並建議替代日期
   - 若有衝突：婉拒並建議替代日期
   - 若可以：確認出席
5. 急件：確認收到並表示會處理

請用專業但友善的語氣撰寫回覆。
"""


def generate_reply(state: AgentState) -> Command[Literal["check_guardrails", "finalize"]]:
    """生成回覆"""
    category = state.get("category", "")
    email = state["email"]
    sender = email["sender"]

    logger.info(f"[Reply] 生成回覆: {email['subject']}")

    # 自動通知類不回覆，直接結束
    if "no-reply" in sender or "noreply" in sender:
        logger.info(f"[Reply] 跳過: no-reply 寄件者")
        return Command(update={"reply": None}, goto="finalize")

    # 垃圾郵件不回覆，直接結束
    if category == "垃圾":
        logger.info(f"[Reply] 跳過: 垃圾郵件不回覆")
        return Command(update={"reply": None}, goto="finalize")

    meeting_info = state.get("meeting_info")
    meeting_info_str = "無" if not meeting_info else str(meeting_info)

    llm = get_llm()
    structured_llm = llm.with_structured_output(ReplyResult)

    prompt = REPLY_PROMPT.format(
        sender=email["sender"],
        subject=email["subject"],
        content=email["content"],
        category=category,
        priority=state.get("priority", "?"),
        meeting_info=meeting_info_str,
        is_working_day=state.get("is_working_day", True),
        non_working_reason=state.get("non_working_reason", "無"),
        has_conflict=state.get("has_conflict", False),
        conflict_with=state.get("conflict_with", "無"),
        suggested_dates=state.get("suggested_dates", []),
    )

    result: ReplyResult = structured_llm.invoke(prompt)

    if result.needs_reply:
        logger.info(f"[Reply] 生成回覆: {result.reply[:100]}...")
    else:
        logger.info(f"[Reply] 不需回覆")

    return Command(
        update={"reply": result.reply if result.needs_reply else None},
        goto="check_guardrails",
    )

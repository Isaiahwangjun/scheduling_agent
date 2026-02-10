"""
會議處理 Agent - ReAct Loop
LLM 自主決定呼叫 MCP Tools（從 Server 動態取得）
使用 Pydantic 結構化輸出
"""

import logging
from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent

from ..state import AgentState
from ..mcp_client import get_mcp_tools
from ..llm import get_llm

# Agent Logger
agent_logger = logging.getLogger("agent")


class MeetingResult(BaseModel):
    """會議處理結果"""
    date: str = Field(description="會議日期 YYYY-MM-DD")
    time: str = Field(description="會議時間 HH:MM-HH:MM")
    is_working_day: bool = Field(description="是否為工作日")
    conflict: Optional[str] = Field(default=None, description="衝突的事件名稱，無衝突則為 null")
    added: bool = Field(description="是否已加入行事曆")
    reason: str = Field(description="決策原因")
    suggested_dates: list[str] = Field(
        default_factory=list,
        description="若無法安排，建議的替代日期時段（如 '2026-01-22 14:00-15:00'），最多 3 個"
    )


SYSTEM_PROMPT = """你是會議排程助理。今天是 {today}。

處理會議邀約的原則：
1. 確認日期是否為工作日（週末和國定假日不可安排會議）
2. 確認時段是否有衝突
3. 兩者皆通過才能新增會議；否則建議 2-3 個替代時段
4. 改期請求需先移除舊會議再新增新會議

請善用可用的工具來完成任務。務必確保 is_working_day 欄位正確反映日期檢查結果。
"""


def _log_messages(messages: list) -> None:
    """記錄 Agent 執行過程（配對 tool call 和回傳結果）"""
    # 收集所有 ToolMessage，用 tool_call_id 索引
    tool_results: dict[str, ToolMessage] = {}
    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_results[msg.tool_call_id] = msg

    for msg in messages:
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    agent_logger.info(f"[Agent] 呼叫工具: {tc['name']}")
                    agent_logger.info(f"[Agent]   參數: {tc['args']}")
                    # 立即輸出對應的 tool 回傳結果
                    tool_call_id = tc.get("id")
                    if tool_call_id and tool_call_id in tool_results:
                        result_msg = tool_results[tool_call_id]
                        content = result_msg.content[:200] + "..." if len(result_msg.content) > 200 else result_msg.content
                        agent_logger.info(f"[Agent]   回傳: {content}")
            elif msg.content:
                # 只顯示前 200 字
                content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                agent_logger.info(f"[Agent] LLM: {content}")


async def meeting_agent(state: AgentState) -> Command[Literal["generate_reply"]]:
    """會議處理 - ReAct Agent with Pydantic structured output"""
    email = state["email"]
    today = state["today"]

    agent_logger.info(f"[Agent] === 處理會議邀約: {email['subject']} ===")

    # 從 MCP Server 動態取得 Tools
    tools = await get_mcp_tools()

    llm = get_llm()
    agent = create_react_agent(
        llm,
        tools,
        response_format=MeetingResult,
    )

    prompt = f"""{SYSTEM_PROMPT.format(today=today)}

郵件：
寄件者: {email["sender"]}
主題: {email["subject"]}
內容: {email["content"]}
"""

    result = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})

    # Log 執行過程
    _log_messages(result["messages"])

    structured: MeetingResult = result["structured_response"]

    agent_logger.info(f"[Agent] 結果: date={structured.date}, is_working_day={structured.is_working_day}, "
                      f"conflict={structured.conflict}, added={structured.added}")
    agent_logger.info(f"[Agent] 原因: {structured.reason}")

    return Command(
        update={
            "meeting_info": structured.model_dump(),
            "is_working_day": structured.is_working_day,
            "has_conflict": structured.conflict is not None,
            "conflict_with": structured.conflict,
            "calendar_action": {"action": "add" if structured.added else "none"},
            "suggested_dates": structured.suggested_dates,
        },
        goto="generate_reply",
    )

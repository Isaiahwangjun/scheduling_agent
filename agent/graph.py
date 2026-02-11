"""
LangGraph 流程組裝
"""

from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    classify,
    meeting_agent,
    generate_reply,
    check_guardrails,
    finalize,
)


def create_graph():
    """
    建立 LangGraph 流程

    流程圖：
                      classify
                         │
          ┌──────────────┼──────────────┐
          │              │              │
       會議邀約         垃圾          其他
          │              │              │
     meeting_agent       │       generate_reply
          │              │              │
     generate_reply      │       check_guardrails
          │              │              │
          └──────────────┴──────────────┘
                         │
                     finalize
                         │
                        END

    meeting_agent 中 LLM 會自主決定呼叫哪些 MCP Tools：
    - check_working_day
    - get_calendar_events
    - add_calendar_event
    - delete_calendar_event
    """
    graph = StateGraph(AgentState)

    # 新增節點
    graph.add_node("classify", classify)
    graph.add_node("meeting_agent", meeting_agent)
    graph.add_node("generate_reply", generate_reply)
    graph.add_node("check_guardrails", check_guardrails)
    graph.add_node("finalize", finalize)

    # 設定入口
    graph.set_entry_point("classify")

    # 路由由 Command 處理
    graph.add_edge("finalize", END)

    return graph.compile()


async def process_email(email: dict, today: str) -> dict:
    """處理單封郵件"""
    graph = create_graph()

    initial_state: AgentState = {
        "email": email,
        "today": today,
    }

    final_state = await graph.ainvoke(initial_state)

    result = {
        "email_id": email["id"],
        "category": final_state.get("category"),
        "priority": final_state.get("priority"),
        "reasoning": final_state.get("reasoning"),
        "meeting_info": final_state.get("meeting_info"),
        "is_working_day": final_state.get("is_working_day"),
        "non_working_reason": final_state.get("non_working_reason"),
        "has_conflict": final_state.get("has_conflict"),
        "conflict_with": final_state.get("conflict_with"),
        "suggested_dates": final_state.get("suggested_dates"),
        "guardrail_triggered": final_state.get("guardrail_triggered"),
        "guardrail_reason": final_state.get("guardrail_reason"),
        "needs_human_review": final_state.get("needs_human_review", False),
        "reply": final_state.get("reply"),
        "calendar_action": final_state.get("calendar_action"),
    }
    # 過濾掉 None 值
    return {k: v for k, v in result.items() if v is not None}

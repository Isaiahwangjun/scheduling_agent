"""
Agent State 定義
"""

from typing import TypedDict, Literal


class MeetingInfo(TypedDict, total=False):
    """會議資訊"""
    date: str  # 2026-01-20
    start_time: str  # 14:00
    end_time: str  # 15:00
    is_reschedule: bool  # 是否為改期請求
    original_date: str | None  # 原會議日期（改期時）


class CalendarAction(TypedDict, total=False):
    """行事曆操作"""
    action: Literal["add", "delete", "none"]
    title: str
    start: str  # ISO format
    end: str
    delete_title: str | None  # 改期時需刪除的舊會議


class AgentState(TypedDict, total=False):
    """Agent 處理單封郵件的狀態"""
    # 輸入
    email: dict
    today: str

    # 分類結果
    category: Literal["急件", "一般", "詢價", "會議邀約", "垃圾"]
    priority: int  # 1-5

    # 會議分析（僅會議邀約）
    meeting_info: MeetingInfo | None

    # 護欄檢查
    guardrail_triggered: bool
    guardrail_reason: str | None

    # 行事曆檢查
    is_working_day: bool
    non_working_reason: str | None
    has_conflict: bool
    conflict_with: str | None
    suggested_dates: list[str]

    # 行事曆操作
    calendar_action: CalendarAction | None

    # 回覆
    reply: str | None
    reasoning: str

    # 最終結果
    needs_human_review: bool

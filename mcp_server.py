"""
Calendar MCP Server

啟動: python mcp_server.py
"""

from mcp.server.fastmcp import FastMCP
from datetime import date, datetime, timedelta
import json
from pathlib import Path

mcp = FastMCP("Calendar")

# 2026 台灣假日
HOLIDAYS_2026 = {
    date(2026, 1, 1): "元旦",
    date(2026, 2, 14): "春節假期",
    date(2026, 2, 15): "小年夜",
    date(2026, 2, 16): "除夕",
    date(2026, 2, 17): "春節",
    date(2026, 2, 18): "春節",
    date(2026, 2, 19): "春節",
    date(2026, 2, 20): "春節假期",
    date(2026, 2, 28): "和平紀念日",
    date(2026, 4, 4): "兒童節",
    date(2026, 4, 5): "清明節",
    date(2026, 5, 1): "勞動節",
    date(2026, 5, 31): "端午節",
    date(2026, 10, 1): "中秋節",
    date(2026, 10, 10): "國慶日",
}


def _is_working_day(d: date) -> tuple[bool, str | None]:
    """判斷是否為工作日"""
    if d.weekday() == 5:
        return False, "週六"
    if d.weekday() == 6:
        return False, "週日"
    if d in HOLIDAYS_2026:
        return False, HOLIDAYS_2026[d]
    return True, None


def _get_next_working_days(from_date: date, count: int = 3) -> list[date]:
    """取得接下來的工作日"""
    result = []
    current = from_date
    while len(result) < count:
        current += timedelta(days=1)
        if _is_working_day(current)[0]:
            result.append(current)
    return result

# 原始資料（唯讀）
ORIGINAL_FILE = Path(__file__).parent / "data" / "calendar.json"
# 工作檔案（可寫）
WORKING_FILE = Path(__file__).parent / "output" / "calendar.json"


def _load() -> list[dict]:
    # 優先讀取工作檔案，若不存在則讀取原始檔案
    if WORKING_FILE.exists():
        with open(WORKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    if ORIGINAL_FILE.exists():
        with open(ORIGINAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save(events: list[dict]) -> None:
    # 確保 output 目錄存在
    WORKING_FILE.parent.mkdir(exist_ok=True)
    events.sort(key=lambda x: x["start"])
    with open(WORKING_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


@mcp.tool()
def get_calendar_events(start_date: str = None, end_date: str = None) -> list[dict]:
    """查詢行事曆事件，檢查時間衝突或尋找可用時段。

    使用時機：
    - 確認 check_working_day 回傳工作日後，查詢該日是否有衝突
    - 尋找替代時段時，查詢鄰近日期的行程

    衝突判斷：回傳所有與查詢時段重疊的事件。若有回傳事件，即表示有衝突。

    Args:
        start_date: 篩選開始時間（ISO 格式，如 2026-01-20 或 2026-01-20T14:00:00）
        end_date: 篩選結束時間（ISO 格式）

    Returns:
        與查詢時段重疊的事件列表，每個事件包含 title, start, end
    """
    events = _load()

    if start_date and end_date:
        # 找出與查詢時段重疊的事件
        query_start = datetime.fromisoformat(start_date)
        query_end = datetime.fromisoformat(end_date)
        events = [
            e for e in events
            if datetime.fromisoformat(e["start"]) < query_end
            and datetime.fromisoformat(e["end"]) > query_start
        ]
    elif start_date:
        # 只有 start_date：找該時間點之後的事件
        start = datetime.fromisoformat(start_date)
        events = [e for e in events if datetime.fromisoformat(e["end"]) > start]

    return events


@mcp.tool()
def add_calendar_event(title: str, start: str, end: str) -> dict:
    """新增行事曆事件。

    ⚠️ 呼叫此工具前，必須先完成以下檢查：
    1. 呼叫 check_working_day 確認該日為工作日（is_working=true）
    2. 呼叫 get_calendar_events 確認無時間衝突

    若為「改期」請求（如「1/27 改到 1/23」）：
    - 先呼叫 delete_calendar_event 刪除舊會議
    - 再呼叫此工具新增新會議

    Args:
        title: 事件標題（如「合作洽談」「視訊會議」）
        start: 開始時間（ISO 格式，如 2026-01-20T14:00:00）
        end: 結束時間（ISO 格式，如 2026-01-20T15:00:00）

    Returns:
        成功: {"success": true, "event": {...}}
        衝突: {"success": false, "reason": "conflict", "conflict_with": "衝突事件名稱"}
    """
    events = _load()
    new_start = datetime.fromisoformat(start)
    new_end = datetime.fromisoformat(end)

    # 檢查衝突
    for e in events:
        e_start = datetime.fromisoformat(e["start"])
        e_end = datetime.fromisoformat(e["end"])
        if new_start < e_end and new_end > e_start:
            return {
                "success": False,
                "reason": "conflict",
                "conflict_with": e["title"],
            }

    new_event = {"title": title, "start": start, "end": end}
    events.append(new_event)
    _save(events)

    return {"success": True, "event": new_event}


@mcp.tool()
def delete_calendar_event(title: str = None, start: str = None) -> dict:
    """刪除行事曆事件。

    使用時機：
    - 處理「改期」請求時，必須先刪除舊會議再新增新會議
    - 例如：郵件說「1/27 改到 1/23」→ 先刪除 1/27，再新增 1/23

    ⚠️ 改期請求的正確流程：
    1. delete_calendar_event(start="2026-01-27T14:00:00")  # 刪除舊的
    2. check_working_day("2026-01-23")  # 檢查新日期
    3. add_calendar_event(...)  # 新增新的

    Args:
        title: 依標題刪除（部分匹配，如「視訊會議」）
        start: 依開始時間刪除（ISO 格式，如 2026-01-27T14:00:00）

    Returns:
        成功: {"success": true, "deleted_count": 刪除數量}
        失敗: {"success": false, "reason": "錯誤原因"}
    """
    if not title and not start:
        return {"success": False, "reason": "需提供 title 或 start"}

    events = _load()
    original_count = len(events)

    if title:
        events = [e for e in events if title.lower() not in e["title"].lower()]
    elif start:
        events = [e for e in events if e["start"] != start]

    deleted = original_count - len(events)
    if deleted == 0:
        return {"success": False, "reason": "找不到符合的事件"}

    _save(events)
    return {"success": True, "deleted_count": deleted}


@mcp.tool()
def check_working_day(date_str: str) -> dict:
    """檢查日期是否為工作日（排除週末和國定假日）。

    ⚠️ 處理會議邀約時，必須首先呼叫此工具！

    使用時機：
    - 收到會議邀約時，先檢查邀約日期是否為工作日
    - 在呼叫 add_calendar_event 之前，務必先確認日期

    重要規則：
    - 若 is_working=false，絕對不可在該日安排會議
    - 非工作日包括：週六、週日、國定假日（除夕、春節、清明等）
    - 若為非工作日，使用 suggested_alternatives 建議替代日期

    Args:
        date_str: 日期，格式為 YYYY-MM-DD（如 2026-01-20）

    Returns:
        - date: 查詢的日期
        - is_working: true/false
        - reason: 若為非工作日，說明原因（如「週六」「除夕」）
        - suggested_alternatives: 若為非工作日，提供 3 個替代工作日
    """
    d = date.fromisoformat(date_str)
    is_working, reason = _is_working_day(d)

    result = {"date": date_str, "is_working": is_working}

    if not is_working:
        result["reason"] = reason
        alternatives = _get_next_working_days(d, 3)
        result["suggested_alternatives"] = [a.isoformat() for a in alternatives]

    return result


if __name__ == "__main__":
    mcp.run()

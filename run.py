"""
Email Agent 主程式

執行: python run.py
"""

from dotenv import load_dotenv
load_dotenv()

import json
import logging
from pathlib import Path
from agent import process_email

# 設定 logging
LOG_FILE = Path(__file__).parent / "output" / "agent.log"
LOG_FILE.parent.mkdir(exist_ok=True)

# 建立 handlers
file_handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
console_handler = logging.StreamHandler()

# 設定格式
formatter = logging.Formatter("%(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 設定 root logger
logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

# Agent logger
logging.getLogger("agent").setLevel(logging.INFO)

# 關閉不需要的 log
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Agent logger（用於分隔線）
agent_logger = logging.getLogger("agent")

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

TODAY = "2026-01-19"

# 工作用行事曆（MCP Server 會操作這個檔案）
WORKING_CALENDAR = OUTPUT_DIR / "calendar.json"


def load_emails() -> list[dict]:
    """載入郵件"""
    with open(DATA_DIR / "emails.json", "r", encoding="utf-8") as f:
        emails = json.load(f)
    emails.sort(key=lambda x: x["timestamp"])
    return emails


def load_original_calendar() -> list[dict]:
    """載入原始行事曆"""
    with open(DATA_DIR / "calendar.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_calendar() -> list[dict]:
    """載入目前行事曆（工作檔案）"""
    if WORKING_CALENDAR.exists():
        with open(WORKING_CALENDAR, "r", encoding="utf-8") as f:
            return json.load(f)
    return load_original_calendar()


def reset_working_calendar():
    """重置工作行事曆為原始狀態"""
    original = load_original_calendar()
    with open(WORKING_CALENDAR, "w", encoding="utf-8") as f:
        json.dump(original, f, indent=2, ensure_ascii=False)


async def main():
    print("\n" + "=" * 60)
    print("Email Agent (LangGraph + MCP)")
    print(f"今天: {TODAY}")
    print("=" * 60)

    # 重置工作行事曆
    reset_working_calendar()

    emails = load_emails()
    print(f"\n{len(emails)} 封郵件待處理")

    print(f"\n初始行事曆:")
    for e in load_original_calendar():
        print(f"   - {e['title']}: {e['start']}")

    results = []

    for i, email in enumerate(emails, 1):
        print("\n" + "-" * 60)
        print(f"[{i}/{len(emails)}] {email['id']}: {email['subject']}")
        print(f"寄件者: {email['sender']}")
        print("-" * 60)

        # Log 分隔線
        agent_logger.info("")
        agent_logger.info("=" * 60)
        agent_logger.info(f"[{i}/{len(emails)}] {email['id']}: {email['subject']}")
        agent_logger.info("=" * 60)

        result = await process_email(email, TODAY)
        results.append(result)

        # 顯示結果
        print(f"分類: {result.get('category', '?')}")
        print(f"優先級: {result.get('priority', '?')}")
        print(f"理由: {result.get('reasoning', '?')}")

        if result.get("meeting_info"):
            info = result["meeting_info"]
            print(f"會議日期: {info.get('date')} {info.get('start_time')}-{info.get('end_time')}")

        if not result.get("is_working_day", True):
            print(f"非工作日: {result.get('non_working_reason')}")
            print(f"建議日期: {result.get('suggested_dates')}")

        if result.get("has_conflict"):
            print(f"時間衝突: {result.get('conflict_with')}")
            print(f"建議日期: {result.get('suggested_dates')}")

        if result.get("guardrail_triggered"):
            print(f"護欄觸發: {result.get('guardrail_reason')}")

        if result.get("needs_human_review"):
            print(">>> 需人工審核 <<<")

        if result.get("reply"):
            print(f"\n回覆內容:\n{result['reply']}")

    # 統計
    print("\n" + "=" * 60)
    print("處理完成")
    print("=" * 60)

    cats = {}
    for r in results:
        c = r.get("category", "?")
        cats[c] = cats.get(c, 0) + 1

    print("\n分類統計:")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"   {c}: {n}")

    human_review = [r for r in results if r.get("needs_human_review")]
    print(f"\n需人工審核: {len(human_review)} 封")

    # 最終行事曆
    print(f"\n最終行事曆:")
    for e in load_calendar():
        print(f"   - {e['title']}: {e['start']}")

    # 儲存結果
    with open(OUTPUT_DIR / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_DIR / "calendar_final.json", "w", encoding="utf-8") as f:
        json.dump(load_calendar(), f, indent=2, ensure_ascii=False)

    print(f"\n結果已儲存至 output/")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

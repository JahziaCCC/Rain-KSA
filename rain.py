import os
import re
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

URL = "https://www.yanbuweather.com/pages/RainAmounts/"

ENTRY_RE = re.compile(
    r"(?P<rank>\d+)\.\s*"
    r"(?P<location>.+?)\s*:\s*"
    r"(?P<amount>\d+(?:\.\d+)?)\s*ملم\s*"
    r"\(من الساعة:\s*(?P<start>.*?)\s*إلى الساعة:\s*(?P<end>.*?)\)"
    r"(?:\s*(?P<ongoing>الهطول مستمر))?",
    re.DOTALL
)

def get_day_ar(day_en: str) -> str:
    days = {
        "Monday": "الاثنين",
        "Tuesday": "الثلاثاء",
        "Wednesday": "الأربعاء",
        "Thursday": "الخميس",
        "Friday": "الجمعة",
        "Saturday": "السبت",
        "Sunday": "الأحد",
    }
    return days.get(day_en, day_en)

def classify(amount: float) -> str:
    if amount >= 50:
        return "غزير جدًا"
    if amount >= 25:
        return "غزير"
    if amount >= 10:
        return "متوسط"
    return "خفيف"

def fetch_text_with_playwright() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 2400})

        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

            body_text = page.locator("body").inner_text(timeout=15000)

            # لو فيه تحميل متأخر، نجرب ننتظر قليلًا مرة ثانية
            if "ملم" not in body_text:
                page.wait_for_timeout(5000)
                body_text = page.locator("body").inner_text(timeout=15000)

            return body_text

        finally:
            browser.close()

def extract_items(text: str, limit: int = 15) -> list[dict]:
    matches = list(ENTRY_RE.finditer(text))
    items = []

    for m in matches[:limit]:
        location = " ".join(m.group("location").split())
        start = " ".join(m.group("start").split())
        end = " ".join(m.group("end").split())

        items.append({
            "rank": int(m.group("rank")),
            "location": location,
            "amount": float(m.group("amount")),
            "start": start,
            "end": end,
            "ongoing": bool(m.group("ongoing")),
        })

    return items

def build_report(text: str) -> str:
    now = datetime.now()
    header = (
        "تقرير الهاطل المطري - المملكة العربية السعودية\n\n"
        f"اليوم: {get_day_ar(now.strftime('%A'))}\n"
        f"التاريخ: {now.strftime('%Y-%m-%d')}\n"
        f"الوقت: {now.strftime('%H:%M')}\n\n"
    )

    items = extract_items(text, limit=15)

    if not items:
        return header + "تعذر استخراج بيانات الهطول من الصفحة."

    high_rain = [x for x in items if x["amount"] >= 50]
    ongoing_rain = [x for x in items if x["ongoing"]]

    parts = [header]

    if high_rain:
        parts.append("التنبيهات:\n")
        for item in high_rain:
            parts.append(
                f"- {item['location']}: {item['amount']} ملم ({classify(item['amount'])})\n"
            )
            parts.append(f"  من الساعة {item['start']} إلى الساعة {item['end']}\n")
            if item["ongoing"]:
                parts.append("  الهطول مازال مستمر\n")
        parts.append("\n")

    parts.append("أعلى كميات الهطول المسجلة:\n\n")

    for i, item in enumerate(items, 1):
        parts.append(
            f"{i}. {item['location']}: {item['amount']} ملم - {classify(item['amount'])}\n"
        )
        parts.append(f"   من الساعة {item['start']} إلى الساعة {item['end']}\n")
        if item["ongoing"]:
            parts.append("   الهطول مازال مستمر\n")

    if ongoing_rain:
        parts.append("\nالمواقع التي مازال فيها الهطول مستمر:\n")
        for item in ongoing_rain:
            parts.append(f"- {item['location']}: {item['amount']} ملم\n")

    return "".join(parts)

def send_message(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise ValueError("Telegram secrets missing")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(
        url,
        data={"chat_id": chat_id, "text": message},
        timeout=30,
    )
    response.raise_for_status()

def main() -> None:
    text = fetch_text_with_playwright()
    report = build_report(text)
    send_message(report)

if __name__ == "__main__":
    try:
        main()
        print("DONE")
    except Exception as e:
        error_msg = f"Rain-KSA Error:\n{str(e)}"
        print(error_msg)
        try:
            send_message(error_msg)
        except Exception:
            raise

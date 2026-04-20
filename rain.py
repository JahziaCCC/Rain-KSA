import os
import re
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://www.yanbuweather.com/pages/RainAmounts/"

LINE_PATTERN = re.compile(
    r"^\s*"
    r"(?P<location>.+?)\s*:\s*"
    r"(?P<amount>\d+(?:\.\d+)?)\s*ملم\s*"
    r"\(من الساعة:\s*(?P<start>.+?)\s*إلى الساعة:\s*(?P<end>.+?)\)"
    r"(?:\s*(?P<ongoing>الهطول مستمر))?\s*$"
)

def get_day_ar(day_en):
    days = {
        "Monday": "الاثنين",
        "Tuesday": "الثلاثاء",
        "Wednesday": "الأربعاء",
        "Thursday": "الخميس",
        "Friday": "الجمعة",
        "Saturday": "السبت",
        "Sunday": "الأحد"
    }
    return days.get(day_en, day_en)

def classify(amount):
    if amount >= 50:
        return "غزير جدًا"
    elif amount >= 25:
        return "غزير"
    elif amount >= 10:
        return "متوسط"
    else:
        return "خفيف"

def fetch_text():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 2400})
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            text = page.locator("body").inner_text(timeout=15000)
            return text
        finally:
            browser.close()

def extract_lines(text, limit=15):
    lines = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split()).strip()

        if (
            ":" in line
            and "ملم" in line
            and "من الساعة:" in line
            and "إلى الساعة:" in line
        ):
            lines.append(line)

        if len(lines) >= limit:
            break

    return lines

def parse_line(line):
    match = LINE_PATTERN.match(line)
    if not match:
        return None

    return {
        "location": match.group("location").strip(),
        "amount": float(match.group("amount")),
        "start": match.group("start").strip(),
        "end": match.group("end").strip(),
        "ongoing": bool(match.group("ongoing")),
    }

def build_report(text):
    now = datetime.now()
    header = (
        "تقرير الهاطل المطري - المملكة العربية السعودية\n\n"
        f"اليوم: {get_day_ar(now.strftime('%A'))}\n"
        f"التاريخ: {now.strftime('%Y-%m-%d')}\n"
        f"الوقت: {now.strftime('%H:%M')}\n\n"
    )

    raw_lines = extract_lines(text, limit=15)
    items = []

    for line in raw_lines:
        item = parse_line(line)
        if item:
            items.append(item)

    if not items:
        preview = "\n".join(raw_lines[:5]) if raw_lines else "لم يتم العثور على أسطر مطابقة."
        return header + "تعذر استخراج بيانات الهطول من الصفحة.\n\nمعاينة:\n" + preview

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

def send_message(message):
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

def main():
    text = fetch_text()
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

import os
import re
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://www.yanbuweather.com/pages/RainAmounts/"

ENTRY_PATTERN = re.compile(
    r"(?P<rank>\d+)\.\s*"
    r"(?P<location>[^:\n]+?)\s*:\s*"
    r"(?P<amount>\d+(?:\.\d+)?)\s*ملم\s*"
    r"\(من الساعة:\s*(?P<start>.*?)\s*إلى الساعة:\s*(?P<end>.*?)\)"
    r"(?:\s*(?P<ongoing>الهطول مستمر))?",
    re.DOTALL
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

def normalize_text(text):
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text

def extract_items(text, limit=15):
    text = normalize_text(text)
    matches = list(ENTRY_PATTERN.finditer(text))
    items = []

    for match in matches[:limit]:
        items.append({
            "rank": int(match.group("rank")),
            "location": match.group("location").strip(),
            "amount": float(match.group("amount")),
            "start": match.group("start").strip(),
            "end": match.group("end").strip(),
            "ongoing": bool(match.group("ongoing"))
        })

    return items

def build_report(text):
    items = extract_items(text, limit=15)
    now = datetime.now()

    msg = ""
    msg += "تقرير الهاطل المطري - المملكة العربية السعودية\n\n"
    msg += f"اليوم: {get_day_ar(now.strftime('%A'))}\n"
    msg += f"التاريخ: {now.strftime('%Y-%m-%d')}\n"
    msg += f"الوقت: {now.strftime('%H:%M')}\n\n"

    if not items:
        msg += "تعذر استخراج بيانات الهطول من الصفحة.\n\n"
        msg += "معاينة:\n"
        msg += normalize_text(text)[:1500]
        return msg

    high_rain = [x for x in items if x["amount"] >= 50]
    ongoing_rain = [x for x in items if x["ongoing"]]

    if high_rain:
        msg += "التنبيهات:\n"
        for item in high_rain:
            msg += f"- {item['location']}: {item['amount']} ملم ({classify(item['amount'])})\n"
            msg += f"  من الساعة {item['start']} إلى الساعة {item['end']}\n"
            if item["ongoing"]:
                msg += "  الهطول مازال مستمر\n"
        msg += "\n"

    msg += "أعلى كميات الهطول المسجلة:\n\n"

    for i, item in enumerate(items, 1):
        msg += f"{i}. {item['location']}: {item['amount']} ملم - {classify(item['amount'])}\n"
        msg += f"   من الساعة {item['start']} إلى الساعة {item['end']}\n"
        if item["ongoing"]:
            msg += "   الهطول مازال مستمر\n"

    if ongoing_rain:
        msg += "\nالمواقع التي مازال فيها الهطول مستمر:\n"
        for item in ongoing_rain:
            msg += f"- {item['location']}: {item['amount']} ملم\n"

    return msg

def send_message(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise ValueError("Telegram secrets missing")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(
        url,
        data={"chat_id": chat_id, "text": message},
        timeout=30
    )
    response.raise_for_status()
    print("DONE")

if __name__ == "__main__":
    try:
        text = fetch_text()
        report = build_report(text)
        send_message(report)
    except Exception as e:
        error_msg = f"Rain-KSA Error:\n{str(e)}"
        print(error_msg)
        try:
            send_message(error_msg)
        except Exception:
            raise

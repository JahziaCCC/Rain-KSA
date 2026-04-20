import os
import re
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://www.yanbuweather.com/pages/RainAmounts/"

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
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        text = page.locator("body").inner_text()
        browser.close()
        return text

def extract_lines(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # فقط السطور التي تبدأ برقم ثم نقطة
    rain_lines = []
    for line in lines:
        if re.match(r"^\d+\.\s", line):
            rain_lines.append(line)

    return rain_lines[:15]

def parse_line(line):
    pattern = re.compile(
        r"^\d+\.\s*"
        r"(?P<location>.+?)\s*:\s*"
        r"(?P<amount>\d+(?:\.\d+)?)\s*ملم\s*"
        r"\(من الساعة:\s*(?P<start>.*?)\s*إلى الساعة:\s*(?P<end>.*?)\)"
        r"(?:\s*(?P<ongoing>الهطول مستمر))?\s*$"
    )

    m = pattern.match(line)
    if not m:
        return None

    return {
        "location": m.group("location").strip(),
        "amount": float(m.group("amount")),
        "start": m.group("start").strip(),
        "end": m.group("end").strip(),
        "ongoing": bool(m.group("ongoing"))
    }

def build_report(text):
    lines = extract_lines(text)
    items = []

    for line in lines:
        item = parse_line(line)
        if item:
            items.append(item)

    now = datetime.now()

    msg = ""
    msg += "تقرير الهاطل المطري - المملكة العربية السعودية\n\n"
    msg += f"اليوم: {get_day_ar(now.strftime('%A'))}\n"
    msg += f"التاريخ: {now.strftime('%Y-%m-%d')}\n"
    msg += f"الوقت: {now.strftime('%H:%M')}\n\n"

    if not items:
        msg += "تعذر استخراج بيانات الهطول من الصفحة.\n"
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

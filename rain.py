import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://www.yanbuweather.com/pages/RainAmounts/"

def fetch_text():
    r = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)
    return text

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

def extract_items(text):
    lines = text.splitlines()
    items = []

    pattern = re.compile(
        r"(?P<location>.+?)\s*:\s*"
        r"(?P<amount>\d+(?:\.\d+)?)\s*ملم\s*"
        r"\(من الساعة:\s*(?P<start>.*?)\s*إلى الساعة:\s*(?P<end>.*?)\)"
        r"(?:\s*(?P<ongoing>الهطول مستمر))?"
    )

    for line in lines:
        line = line.strip()
        if "ملم" not in line or "من الساعة:" not in line:
            continue

        m = pattern.search(line)
        if not m:
            continue

        location = m.group("location").strip()

        # تنظيف الترقيم لو كان موجود في البداية مثل 1. أو 12.
        location = re.sub(r"^\d+\.\s*", "", location).strip()

        items.append({
            "location": location,
            "amount": float(m.group("amount")),
            "start": m.group("start").strip(),
            "end": m.group("end").strip(),
            "ongoing": bool(m.group("ongoing"))
        })

    return items[:15]

def build_report(text):
    items = extract_items(text)
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
        data={
            "chat_id": chat_id,
            "text": message
        },
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

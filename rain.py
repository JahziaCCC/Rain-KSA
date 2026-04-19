import os
import re
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://www.yanbuweather.com/pages/RainAmounts/"
STATE_FILE = "last_report_hash.txt"

HIGH_THRESHOLD = 40.0
MEDIUM_THRESHOLD = 20.0


def fetch_text():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(URL, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text("\n", strip=True)
    return text


def get_day_name_arabic(day_en):
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


def parse_rain_line(line):
    """
    مثال متوقع:
    البير (منطقة الرياض): 51.8 ملم من الساعة 04:30 م إلى الساعة 06:25 م
    أو:
    الدرعية (منطقة الرياض): 43.8 ملم من الساعة 03:00 م إلى الساعة 06:25 م الهطول مستمر
    """

    pattern = re.compile(
        r"^(?P<location>.+?)\s*:\s*"
        r"(?P<amount>\d+(?:\.\d+)?)\s*ملم"
        r"(?:\s*من الساعة\s*(?P<start>.+?)\s*إلى الساعة\s*(?P<end>.+?))?"
        r"(?:\s*(?P<ongoing>الهطول مستمر))?$"
    )

    match = pattern.search(line.strip())

    if not match:
        return {
            "raw": line.strip(),
            "location": line.strip(),
            "amount": None,
            "start": None,
            "end": None,
            "ongoing": False
        }

    amount_text = match.group("amount")
    amount_value = float(amount_text) if amount_text else None

    return {
        "raw": line.strip(),
        "location": match.group("location").strip(),
        "amount": amount_value,
        "start": match.group("start").strip() if match.group("start") else None,
        "end": match.group("end").strip() if match.group("end") else None,
        "ongoing": True if match.group("ongoing") else False
    }


def classify_rain(amount):
    if amount is None:
        return None
    if amount >= HIGH_THRESHOLD:
        return "عالي"
    if amount >= MEDIUM_THRESHOLD:
        return "متوسط"
    return "خفيف"


def extract_rain_lines(text):
    lines = text.splitlines()
    rain_lines = [line.strip() for line in lines if "ملم" in line]
    return rain_lines[:15]


def build_report(text):
    rain_lines = extract_rain_lines(text)

    now = datetime.now()
    day_en = now.strftime("%A")
    day_ar = get_day_name_arabic(day_en)
    date_text = now.strftime("%Y-%m-%d")
    time_text = now.strftime("%H:%M")

    if not rain_lines:
        return (
            "تقرير الهاطل المطري - المملكة العربية السعودية\n\n"
            f"اليوم: {day_ar}\n"
            f"التاريخ: {date_text}\n"
            f"الوقت: {time_text}\n\n"
            "لا توجد بيانات حالياً"
        )

    parsed_lines = [parse_rain_line(line) for line in rain_lines]

    high_rain = [item for item in parsed_lines if item["amount"] is not None and item["amount"] >= HIGH_THRESHOLD]
    ongoing_rain = [item for item in parsed_lines if item["ongoing"]]

    msg = ""
    msg += "تقرير الهاطل المطري - المملكة العربية السعودية\n\n"
    msg += f"اليوم: {day_ar}\n"
    msg += f"التاريخ: {date_text}\n"
    msg += f"الوقت: {time_text}\n\n"

    if high_rain:
        msg += "التنبيهات:\n"
        for item in high_rain:
            msg += f"- {item['location']}: {item['amount']} ملم (هطول عالي)\n"
        msg += "\n"

    msg += "أعلى كميات الهطول المسجلة:\n\n"

    for i, item in enumerate(parsed_lines, 1):
        if item["amount"] is not None:
            level = classify_rain(item["amount"])
            msg += f"{i}. {item['location']}: {item['amount']} ملم"
            if level:
                msg += f" - {level}"
            msg += "\n"
        else:
            msg += f"{i}. {item['location']}\n"

        if item["start"] and item["end"]:
            msg += f"   من الساعة {item['start']} إلى الساعة {item['end']}\n"

        if item["ongoing"]:
            msg += "   الهطول مازال مستمر\n"

    if ongoing_rain:
        msg += "\nالمواقع التي مازال فيها الهطول مستمر:\n"
        for item in ongoing_rain:
            msg += f"- {item['location']}"
            if item["amount"] is not None:
                msg += f": {item['amount']} ملم"
            msg += "\n"

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

    print("TELEGRAM STATUS:", response.status_code)
    print("TELEGRAM RESPONSE:", response.text)
    response.raise_for_status()


def get_report_hash(report_text):
    return hashlib.sha256(report_text.encode("utf-8")).hexdigest()


def load_last_hash():
    if not os.path.exists(STATE_FILE):
        return None

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def save_current_hash(report_hash):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(report_hash)


if __name__ == "__main__":
    try:
        text = fetch_text()
        report = build_report(text)

        current_hash = get_report_hash(report)
        last_hash = load_last_hash()

        if current_hash != last_hash:
            send_message(report)
            save_current_hash(current_hash)
            print("NEW REPORT SENT")
        else:
            print("NO CHANGE - REPORT NOT SENT")

    except Exception as e:
        error_msg = f"Rain-KSA Error:\n{str(e)}"
        print(error_msg)

        try:
            send_message(error_msg)
        except Exception as inner:
            print("FAILED TO SEND ERROR TO TELEGRAM:", str(inner))
            raise

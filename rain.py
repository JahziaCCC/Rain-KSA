import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://www.yanbuweather.com/pages/RainAmounts/"

def fetch_text():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(URL, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    return soup.get_text("\n", strip=True)

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

def classify_rain(amount):
    if amount is None:
        return None
    if amount >= 50:
        return "غزير جدًا"
    if amount >= 25:
        return "غزير"
    if amount >= 10:
        return "متوسط"
    return "خفيف"

def parse_rain_line(line):
    line = line.strip()

    location_match = re.search(r"^(.*?):\s*(\d+(?:\.\d+)?)\s*ملم", line)
    if not location_match:
        return {
            "location": line,
            "amount": None,
            "start": None,
            "end": None,
            "ongoing": False
        }

    location = location_match.group(1).strip()
    amount = float(location_match.group(2))

    start_match = re.search(r"من الساعة\s*(.*?)\s*إلى الساعة", line)
    end_match = re.search(r"إلى الساعة\s*(.*?)(?:\s*الهطول مستمر|$)", line)
    ongoing = "الهطول مستمر" in line

    start_time = start_match.group(1).strip() if start_match else None
    end_time = end_match.group(1).strip() if end_match else None

    return {
        "location": location,
        "amount": amount,
        "start": start_time,
        "end": end_time,
        "ongoing": ongoing
    }

def build_report(text):
    lines = text.splitlines()
    rain_lines = [line.strip() for line in lines if "ملم" in line][:15]

    now = datetime.now()
    day_ar = get_day_name_arabic(now.strftime("%A"))
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

    parsed = [parse_rain_line(line) for line in rain_lines]
    high_rain = [item for item in parsed if item["amount"] is not None and item["amount"] >= 50]
    ongoing_rain = [item for item in parsed if item["ongoing"]]

    msg = ""
    msg += "تقرير الهاطل المطري - المملكة العربية السعودية\n\n"
    msg += f"اليوم: {day_ar}\n"
    msg += f"التاريخ: {date_text}\n"
    msg += f"الوقت: {time_text}\n\n"

    if high_rain:
        msg += "التنبيهات:\n"
        for item in high_rain:
            msg += f"- {item['location']}: {item['amount']} ملم ({classify_rain(item['amount'])})\n"
            if item["start"] and item["end"]:
                msg += f"  من الساعة {item['start']} إلى الساعة {item['end']}\n"
            if item["ongoing"]:
                msg += "  الهطول مازال مستمر\n"
        msg += "\n"

    msg += "أعلى كميات الهطول المسجلة:\n\n"

    for i, item in enumerate(parsed, 1):
        if item["amount"] is not None:
            msg += f"{i}. {item['location']}: {item['amount']} ملم - {classify_rain(item['amount'])}\n"
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
        data={"chat_id": chat_id, "text": message},
        timeout=30
    )

    print("TELEGRAM STATUS:", response.status_code)
    print("TELEGRAM RESPONSE:", response.text)
    response.raise_for_status()

if __name__ == "__main__":
    try:
        text = fetch_text()
        report = build_report(text)
        send_message(report)
        print("DONE")
    except Exception as e:
        error_msg = f"Rain-KSA Error:\n{str(e)}"
        print(error_msg)
        try:
            send_message(error_msg)
        except Exception:
            raise

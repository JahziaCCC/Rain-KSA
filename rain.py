import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://www.yanbuweather.com/pages/RainAmounts/"

def fetch_text():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(URL, headers=headers, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
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

def clean_report(text):
    lines = text.splitlines()
    rain_lines = [line.strip() for line in lines if "ملم" in line]

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

    rain_lines = rain_lines[:15]

    msg = ""
    msg += "تقرير الهاطل المطري - المملكة العربية السعودية\n\n"
    msg += f"اليوم: {day_ar}\n"
    msg += f"التاريخ: {date_text}\n"
    msg += f"الوقت: {time_text}\n\n"
    msg += "أعلى كميات الهطول المسجلة:\n"

    for i, line in enumerate(rain_lines, 1):
        msg += f"{i}. {line}\n"

    return msg

def send(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise ValueError("Telegram secrets missing")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": msg
        },
        timeout=30
    )

    print("TELEGRAM STATUS:", response.status_code)
    print("TELEGRAM RESPONSE:", response.text)
    response.raise_for_status()

if __name__ == "__main__":
    try:
        text = fetch_text()
        report = clean_report(text)
        send(report)
        print("DONE")
    except Exception as e:
        error_msg = f"Rain-KSA Error:\n{str(e)}"
        print(error_msg)
        try:
            send(error_msg)
        except Exception as inner:
            print("FAILED TO SEND ERROR TO TELEGRAM:", str(inner))
            raise

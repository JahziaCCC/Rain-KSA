import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://www.yanbuweather.com/pages/RainAmounts/"

ENTRY_RE = re.compile(
    r"\b(?P<rank>\d+)\.\s*"
    r"(?P<location>.+?)\s*:\s*"
    r"(?P<amount>\d+(?:\.\d+)?)\s*ملم\s*"
    r"\(من الساعة:\s*(?P<start>.*?)\s*إلى الساعة:\s*(?P<end>.*?)\)"
    r"(?:\s*(?P<ongoing>الهطول مستمر))?",
    re.DOTALL
)

def fetch_text():
    headers = {"User-Agent": "Mozilla/5.0"}
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
        "Sunday": "الأحد",
    }
    return days.get(day_en, day_en)

def classify_rain(amount):
    if amount >= 50:
        return "غزير جدًا"
    if amount >= 25:
        return "غزير"
    if amount >= 10:
        return "متوسط"
    return "خفيف"

def extract_entries(text, limit=15):
    entries = []
    for m in ENTRY_RE.finditer(text):
        entries.append({
            "rank": int(m.group("rank")),
            "location": " ".join(m.group("location").split()),
            "amount": float(m.group("amount")),
            "start": " ".join(m.group("start").split()),
            "end": " ".join(m.group("end").split()),
            "ongoing": bool(m.group("ongoing")),
        })
        if len(entries) >= limit:
            break
    return entries

def build_report(text):
    entries = extract_entries(text, limit=15)

    now = datetime.now()
    day_ar = get_day_name_arabic(now.strftime("%A"))
    date_text = now.strftime("%Y-%m-%d")
    time_text = now.strftime("%H:%M")

    header = (
        "تقرير الهاطل المطري - المملكة العربية السعودية\n\n"
        f"اليوم: {day_ar}\n"
        f"التاريخ: {date_text}\n"
        f"الوقت: {time_text}\n\n"
    )

    if not entries:
        return header + "تم العثور على بيانات، لكن تعذر قراءة تنسيق الوقت من الصفحة."

    high_rain = [e for e in entries if e["amount"] >= 50]
    ongoing_rain = [e for e in entries if e["ongoing"]]

    parts = [header]

    if high_rain:
        parts.append("التنبيهات:\n")
        for item in high_rain:
            parts.append(
                f"- {item['location']}: {item['amount']} ملم ({classify_rain(item['amount'])})\n"
            )
            parts.append(f"  من الساعة {item['start']} إلى الساعة {item['end']}\n")
            if item["ongoing"]:
                parts.append("  الهطول مازال مستمر\n")
        parts.append("\n")

    parts.append("أعلى كميات الهطول المسجلة:\n\n")

    for i, item in enumerate(entries, 1):
        parts.append(
            f"{i}. {item['location']}: {item['amount']} ملم - {classify_rain(item['amount'])}\n"
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

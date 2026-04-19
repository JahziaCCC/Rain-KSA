import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://www.yanbuweather.com/pages/RainAmounts/"

def fetch_text():
    r = requests.get(URL, headers={"User-Agent":"Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    return soup.get_text("\n", strip=True)

def get_day_ar(day):
    d = {
        "Monday":"الاثنين",
        "Tuesday":"الثلاثاء",
        "Wednesday":"الأربعاء",
        "Thursday":"الخميس",
        "Friday":"الجمعة",
        "Saturday":"السبت",
        "Sunday":"الأحد"
    }
    return d.get(day, day)

def classify(x):
    if x >= 50:
        return "غزير جدًا"
    elif x >= 25:
        return "غزير"
    elif x >= 10:
        return "متوسط"
    else:
        return "خفيف"

def extract_lines(text):
    lines = text.splitlines()

    # فقط السطور التي تبدأ برقم ونقطة
    rows = []
    for line in lines:
        if re.match(r"^\d+\.", line.strip()):
            rows.append(line.strip())

    return rows[:15]

def parse(line):
    # مثال:
    # 1. آل قحطان (منطقة عسير): 52.5 ملم (من الساعة: 04:50 م إلى الساعة: 06:25 م)

    m = re.search(
        r"^\d+\.\s*(.*?)\:\s*([\d\.]+)\s*ملم\s*\(من الساعة:\s*(.*?)\s*إلى الساعة:\s*(.*?)\)(.*)$",
        line
    )

    if not m:
        return None

    location = m.group(1).strip()
    amount = float(m.group(2))
    start = m.group(3).strip()
    end = m.group(4).strip()
    tail = m.group(5)

    ongoing = "مستمر" in tail

    return {
        "location": location,
        "amount": amount,
        "start": start,
        "end": end,
        "ongoing": ongoing
    }

def build(text):
    rows = extract_lines(text)
    items = []

    for row in rows:
        x = parse(row)
        if x:
            items.append(x)

    now = datetime.now()

    msg = ""
    msg += "تقرير الهاطل المطري - المملكة العربية السعودية\n\n"
    msg += f"اليوم: {get_day_ar(now.strftime('%A'))}\n"
    msg += f"التاريخ: {now.strftime('%Y-%m-%d')}\n"
    msg += f"الوقت: {now.strftime('%H:%M')}\n\n"

    msg += "أعلى كميات الهطول المسجلة:\n\n"

    for i, item in enumerate(items,1):
        msg += f"{i}. {item['location']}: {item['amount']} ملم - {classify(item['amount'])}\n"
        msg += f"   من الساعة {item['start']} إلى الساعة {item['end']}\n"

        if item["ongoing"]:
            msg += "   الهطول مازال مستمر\n"

    return msg

def send(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    requests.post(url, data={
        "chat_id": chat,
        "text": msg
    })

if __name__ == "__main__":
    text = fetch_text()
    report = build(text)
    send(report)

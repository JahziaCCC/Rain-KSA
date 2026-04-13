import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://www.yanbuweather.com/pages/RainAmounts/"

def parse_amount(text):
    text = text.strip().replace("ملم", "").replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    return float(m.group(1)) if m else None

def fetch_data():
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.find_all("tr")
    data = []

    for row in rows:
        cols = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        if len(cols) < 5:
            continue

        city = cols[0]
        amount = parse_amount(cols[1])
        start_time = cols[2]
        end_time = cols[3]
        status = cols[4]

        if amount is None:
            continue

        data.append({
            "city": city,
            "amount": amount,
            "start": start_time,
            "end": end_time,
            "status": status,
        })

    return data

def analyze(data):
    if not data:
        return None

    top_city = max(data, key=lambda x: x["amount"])
    active = [x for x in data if "مستمر" in x["status"]]

    earliest = min(data, key=lambda x: x["start"] if x["start"] else "99:99")
    latest = max(data, key=lambda x: x["end"] if x["end"] else "00:00")

    top5 = sorted(data, key=lambda x: x["amount"], reverse=True)[:5]

    return {
        "count": len(data),
        "top_city": top_city,
        "active": active,
        "earliest": earliest,
        "latest": latest,
        "top5": top5,
    }

def build_report(result):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    msg = f"""
🌧️ تقرير رصد الأمطار
🕒 {now}
════════════════════

📊 عدد المدن: {result['count']}
🏆 أعلى هطول: {result['top_city']['city']} ({result['top_city']['amount']} ملم)

⏱️ أول بداية: {result['earliest']['city']} - {result['earliest']['start']}
🛑 آخر نهاية: {result['latest']['city']} - {result['latest']['end']}

════════════════════
🌦️ أعلى 5 مدن:
"""

    for i, item in enumerate(result["top5"], 1):
        msg += f"{i}. {item['city']} - {item['amount']} ملم\n"

    msg += "\n════════════════════\n📍 الهطول المستمر:\n"

    if result["active"]:
        for a in result["active"][:10]:
            msg += f"• {a['city']} ({a['amount']} ملم)\n"
    else:
        msg += "• لا يوجد\n"

    return msg


def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print(message)
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})


if __name__ == "__main__":
    data = fetch_data()
    result = analyze(data)

    if result:
        report = build_report(result)
        send_telegram(report)
    else:
        print("No data")

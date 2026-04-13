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
    soup = BeautifulSoup(resp.text, "html.parser")

    data = []
    for row in soup.find_all("tr"):
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        if len(cols) < 5:
            continue

        amount = parse_amount(cols[1])
        if amount is None:
            continue

        data.append({
            "city": cols[0],
            "amount": amount,
            "start": cols[2],
            "end": cols[3],
            "status": cols[4],
        })

    return data

def analyze(data):
    if not data:
        return None

    top = max(data, key=lambda x: x["amount"])
    active = [d for d in data if "مستمر" in d["status"]]

    top5 = sorted(data, key=lambda x: x["amount"], reverse=True)[:5]

    return {
        "count": len(data),
        "top": top,
        "active": active,
        "top5": top5
    }

def build_report(r):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

    msg = f"""🌧️ تقرير الأمطار – السعودية
🕒 {now}

📊 عدد المدن: {r['count']}
🏆 الأعلى: {r['top']['city']} ({r['top']['amount']} ملم)

🌦️ أعلى 5:
"""

    for i, t in enumerate(r["top5"], 1):
        msg += f"{i}. {t['city']} - {t['amount']} ملم\n"

    msg += "\n📍 الهطول المستمر:\n"

    if r["active"]:
        for a in r["active"][:10]:
            msg += f"• {a['city']} ({a['amount']} ملم)\n"
    else:
        msg += "• لا يوجد\n"

    return msg

def send(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": msg})

if __name__ == "__main__":
    data = fetch_data()
    r = analyze(data)

    if r:
        report = build_report(r)
        send(report)

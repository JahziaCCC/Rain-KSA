import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

URL = "https://www.yanbuweather.com/pages/RainAmounts/"

PATTERN = re.compile(
    r"\d+\.\s*"
    r"(?P<city>.+?)\s*"
    r"\((?P<region>.+?)\):\s*"
    r"(?P<amount>\d+(?:\.\d+)?)\s*ملم\s*"
    r"\(من الساعة:\s*(?P<start>.+?)\s*إلى الساعة:\s*(?P<end>.+?)\)"
    r"(?:\s*(?P<status>الهطول مستمر))?"
)

def fetch_data():
    resp = requests.get(URL, timeout=30)
    print("PAGE STATUS:", resp.status_code)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text("\n", strip=True)

    matches = list(PATTERN.finditer(text))
    print("MATCHES FOUND:", len(matches))

    data = []
    for m in matches:
        item = {
            "city": m.group("city").strip(),
            "region": m.group("region").strip(),
            "amount": float(m.group("amount")),
            "start": m.group("start").strip(),
            "end": m.group("end").strip(),
            "status": (m.group("status") or "").strip(),
        }
        data.append(item)

    print("DATA COUNT:", len(data))
    return data

def analyze(data):
    if not data:
        return None

    top = max(data, key=lambda x: x["amount"])
    active = [d for d in data if "مستمر" in d["status"]]
    top5 = sorted(data, key=lambda x: x["amount"], reverse=True)[:5]

    # أول بداية وآخر نهاية كنصوص وقت من الصفحة
    earliest = min(data, key=lambda x: x["start"])
    latest = max(data, key=lambda x: x["end"])

    return {
        "count": len(data),
        "top": top,
        "active": active,
        "top5": top5,
        "earliest": earliest,
        "latest": latest,
    }

def build_report(result):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    lines.append("🌧️ تقرير الأمطار – السعودية")
    lines.append(f"🕒 {now}")
    lines.append("════════════════════")
    lines.append(f"📊 عدد المواقع: {result['count']}")
    lines.append(
        f"🏆 الأعلى: {result['top']['city']} - {result['top']['region']} ({result['top']['amount']} ملم)"
    )
    lines.append(
        f"⏱️ أول بداية: {result['earliest']['city']} ({result['earliest']['start']})"
    )
    lines.append(
        f"🛑 آخر نهاية: {result['latest']['city']} ({result['latest']['end']})"
    )
    lines.append("════════════════════")
    lines.append("🌦️ أعلى 5:")

    for i, item in enumerate(result["top5"], 1):
        lines.append(
            f"{i}. {item['city']} - {item['region']} - {item['amount']} ملم"
        )

    lines.append("════════════════════")
    lines.append("📍 الهطول المستمر:")
    if result["active"]:
        for item in result["active"][:10]:
            lines.append(
                f"• {item['city']} - {item['region']} ({item['amount']} ملم)"
            )
    else:
        lines.append("• لا يوجد")

    return "\n".join(lines)

def send(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise ValueError("Telegram secrets missing")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=30)

    print("TELEGRAM STATUS:", r.status_code)
    print("TELEGRAM RESPONSE:", r.text)
    r.raise_for_status()

if __name__ == "__main__":
    try:
        data = fetch_data()
        result = analyze(data)

        if result:
            report = build_report(result)
        else:
            report = "⚠️ Rain-KSA: تم تشغيل النظام لكن لم يتم العثور على بيانات مطر قابلة للقراءة من الصفحة."

        send(report)
        print("DONE")

    except Exception as e:
        error_msg = f"❌ Rain-KSA Error:\n{str(e)}"
        print(error_msg)
        try:
            send(error_msg)
        except Exception as inner:
            print("FAILED TO SEND ERROR TO TELEGRAM:", str(inner))
            raise

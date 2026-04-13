import os
import requests
from bs4 import BeautifulSoup

URL = "https://www.yanbuweather.com/pages/RainAmounts/"

def fetch_text():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(URL, headers=headers, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # خذ النص كامل
    text = soup.get_text("\n", strip=True)

    return text

def clean_report(text):
    lines = text.splitlines()

    # نفلتر فقط السطور اللي فيها "ملم"
    rain_lines = [l for l in lines if "ملم" in l]

    if not rain_lines:
        return "⚠️ لم يتم العثور على بيانات مطر في الصفحة"

    # خذ أول 15 سطر فقط
    rain_lines = rain_lines[:15]

    msg = "🌧️ تقرير الأمطار – مباشر\n\n"

    for line in rain_lines:
        msg += f"{line}\n"

    return msg

def send(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": msg})

if __name__ == "__main__":
    text = fetch_text()
    report = clean_report(text)
    send(report)

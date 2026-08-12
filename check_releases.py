# Программа проверяет новости 1С и присылает новые релизы в Телеграм

import json
import re
import os
import html

import feedparser
import requests

RSS_URL = "https://1.ru/news/rss"   # публичная лента новостей 1С
SEEN_FILE = "seen.json"             # "записная книжка" отправленных новостей
MAX_PER_RUN = 5                     # не больше 5 сообщений за один запуск

# По каким словам ищем "свои" конфигурации
KEYWORDS = [
      "1С",
]


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)


def matches(text):
    # Ищем слово целиком, чтобы "КА" не срабатывало внутри слова "каждая"
    for kw in KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def find_version(text):
    m = re.search(r"\d+\.\d+\.\d+(\.\d+)?", text)
    return m.group(0) if m else "—"


def clean_html(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def send_message(text):
    token = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": text})
    print("Telegram ответил:", r.status_code)


def main():
    seen = load_seen()
    feed = feedparser.parse(RSS_URL)
    sent = 0

    for item in feed.entries:
        title = item.get("title", "")
        link = item.get("link", "")
        description = clean_html(item.get("summary", ""))

        if not matches(title + " " + description):
            continue  # новость не про наши конфигурации — пропускаем

        key = link or title
        if key in seen:
            continue  # уже отправляли раньше

        version = find_version(title + " " + description)

        text = (
            f"🔔 Новый релиз: {title}\n"
            f"🔢 Версия: {version}\n"
            f"🔗 Описание: {link}\n\n"
            f"📝 Что изменилось:\n{description[:1000]}"
        )
        send_message(text)
        seen.add(key)
        sent += 1

        if sent >= MAX_PER_RUN:
            break  # не заваливаем сообщениями за один раз

    save_seen(seen)
    print("Отправлено новостей:", sent)


if __name__ == "__main__":
    main()

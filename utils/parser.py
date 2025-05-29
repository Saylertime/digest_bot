import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
import feedparser
import certifi
from loader import bot
from pg_maker import all_users


HEADERS = {"User-Agent": "Mozilla/5.0"}


def load_seen_links(file_name):
    if not os.path.exists(file_name):
        return set()
    with open(file_name, "r", encoding="utf-8") as f:
        return set(
            line.strip().split(" — ")[-1]
            for line in f if " — " in line
        )


def save_seen_links(entries, file_name):
    with open(file_name, "a", encoding="utf-8") as f:
        for title, link, source in entries:
            f.write(f"{title} — {link}\n")


async def fetch_sostav():
    URL = "https://www.sostav.ru/news/digital"
    BASE_URL = "https://www.sostav.ru"
    SEEN_FILE_SOSTAV = "links.txt"

    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    seen_links = load_seen_links(SEEN_FILE_SOSTAV)
    new_articles = []

    for news in soup.find_all("a", class_="title"):
        title = news.text.strip()
        relative_link = news.get("href", "")
        full_link = BASE_URL + relative_link

        if full_link not in seen_links:
            new_articles.append((title, full_link, "Sostav"))

    save_seen_links(new_articles, SEEN_FILE_SOSTAV)
    return new_articles


async def fetch_vc():
    URL = "https://vc.ru/design"
    BASE_URL = "https://vc.ru"
    SEEN_FILE_VC = "links.txt"

    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    seen_links = load_seen_links(SEEN_FILE_VC)

    new_articles = []

    for article in soup.find_all("div", class_="content content--short"):
        title_block = article.find("div", class_="content-title")
        title = title_block.get_text(strip=True) if title_block else "Нет заголовка"

        link_tag = article.find("a", class_="content__link")
        href = link_tag.get("href") if link_tag else ""
        full_link = urljoin(BASE_URL, href) if href else ""

        if not full_link:
            continue

        if full_link not in seen_links:
            new_articles.append((title, full_link, "VC"))

    save_seen_links(new_articles, SEEN_FILE_VC)
    return new_articles


async def fetch_habr():
    rss_url = "https://habr.com/ru/rss/flows/design/articles/?fl=ru"
    SEEN_FILE_HABR = "links.txt"

    seen_links = load_seen_links(SEEN_FILE_HABR)
    response = requests.get(rss_url, verify=certifi.where())
    feed = feedparser.parse(response.content)

    new_articles = []

    for entry in feed.entries:
        title = entry.title.strip()
        link = entry.link.strip()

        if link not in seen_links:
            new_articles.append((title, link, "Habr"))

    save_seen_links(new_articles, SEEN_FILE_HABR)
    return new_articles


async def fetch_all():
    sostav = await fetch_sostav()
    vc = await fetch_vc()
    habr = await fetch_habr()

    all_articles = sostav + vc + habr
    all_users_ids = await all_users()
    user_ids_str = [str(record["telegram_id"]) for record in all_users_ids]

    parts = []
    current_part = ""

    for title, link, source in all_articles:
        html_line = f'<a href="{link}"><b>{title}</b></a> — {source}\n\n'
        if len(current_part) + len(html_line) <= 4000:
            current_part += html_line
        else:
            parts.append(current_part.strip())
            current_part = html_line

    if current_part:
        parts.append(current_part.strip())
    for user_id in user_ids_str:
        for part in parts:
            try:
                await bot.send_message(str(user_id), str(part), parse_mode="HTML")
            except Exception as e:
                await bot.send_message("68086662", str(e))

import requests
from bs4 import BeautifulSoup
import os
import random
from urllib.parse import urljoin, urlsplit, urlunsplit, urlparse
import feedparser
import certifi
import re
from loader import bot
from pg_maker import all_users
from aiogram.types import FSInputFile


HEADERS = {"User-Agent": "Mozilla/5.0"}


def load_seen_links(file_name):
    if not os.path.exists(file_name):
        return set()
    with open(file_name, "r", encoding="utf-8") as f:
        return set(
            line.strip().rsplit(" — ", 1)[-1]
            for line in f if " — " in line
        )


def save_seen_links(entries, file_name):
    with open(file_name, "a", encoding="utf-8") as f:
        for title, link, source in entries:
            f.write(f"{title} — {link}\n")


async def fetch_sostav():
    URL = "https://www.sostav.ru/news/digital"
    BASE_URL = "https://www.sostav.ru"
    SEEN_FILE_SOSTAV = "links_news.txt"

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

_ARTICLE_RX = re.compile(r"^https?://dsgners\.ru/[^/]+/\d+-", re.I)

def _is_article_link(url: str) -> bool:
    return bool(_ARTICLE_RX.match(url))

def _strip_fragment(url: str) -> str:
    # убираем #comments и прочие фрагменты
    parts = list(urlsplit(url))
    parts[3] = ""  # query не трогаем
    parts[4] = ""  # fragment
    return urlunsplit(parts)

def _extract_clean_title(a_tag) -> str:
    """
    Пытаемся найти нормальный заголовок:
    1) типичные <span class="line-clamp-3"> внутри ссылки
    2) aria-label / title у <a>
    3) прямой текст узла <a> (без вложенных счетчиков)
    4) запасной вариант: самый длинный текстовый фрагмент внутри <a>
    """
    # 1) самый частый вариант на dsgners.ru
    span = a_tag.select_one("span.line-clamp-3") or a_tag.select_one("span.h2") \
           or a_tag.select_one("span.group-hover\\:text-text-tertiary") \
           or a_tag.select_one("span.group-hover\\:text-text-primary")
    if span:
        t = span.get_text(" ", strip=True)
        if t:
            return t

    # 2) aria-label / title
    for attr in ("aria-label", "title"):
        if a_tag.has_attr(attr):
            t = (a_tag.get(attr) or "").strip()
            if t:
                return t

    # 3) прямой текст <a> (без дочерних узлов)
    direct = "".join(a_tag.find_all(string=True, recursive=False)).strip()
    if direct:
        return direct

    # 4) запасной — самый содержательный текст
    texts = [s.strip() for s in a_tag.stripped_strings if s and len(s.strip()) > 2]
    return max(texts, key=len) if texts else ""


async def fetch_dsgners(articles=True):
    URL = "https://dsgners.ru/" if articles else "https://dsgners.ru/news"
    BASE = "https://dsgners.ru/"
    SEEN_FILE = "links.txt" if articles else "links_news.txt"

    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    seen = load_seen_links(SEEN_FILE)
    out, seen_now = [], set()

    # 1) основные карточки
    for a in soup.select("article a[href]"):
        href = a["href"].strip()
        link = urljoin(BASE, href)
        link = _strip_fragment(link)
        if not _is_article_link(link):
            continue

        title = _extract_clean_title(a)
        if not title:
            continue

        if link in seen_now:
            continue
        seen_now.add(link)

        if link not in seen:
            out.append((title, link, "DSGNERS"))

    # 2) подстраховка (если вдруг ничего не нашли на текущей разметке)
    if not out:
        for a in soup.select("a[href]"):
            href = a["href"].strip()
            link = urljoin(BASE, href)
            link = _strip_fragment(link)
            if not _is_article_link(link):
                continue

            title = _extract_clean_title(a)
            if not title:
                continue

            if link in seen_now:
                continue
            seen_now.add(link)

            if link not in seen:
                out.append((title, link, "DSGNERS"))

    save_seen_links(out, SEEN_FILE)
    return out

# async def fetch_all():
#     sostav = await fetch_sostav()
#     vc = await fetch_vc()
#     habr = await fetch_habr()
#
#     all_articles = sostav + vc + habr
#     all_users_ids = await all_users()
#     user_ids_str = [str(record["telegram_id"]) for record in all_users_ids]
#
#     parts = []
#     current_part = ""
#
#     for title, link, source in all_articles:
#         html_line = f'<a href="{link}"><b>{title}</b></a> — {source}\n\n'
#         if len(current_part) + len(html_line) <= 4000:
#             current_part += html_line
#         else:
#             parts.append(current_part.strip())
#             current_part = html_line
#
#     if current_part:
#         parts.append(current_part.strip())
#     for user_id in user_ids_str:
#         for part in parts:
#             try:
#                 await bot.send_message(str(user_id), str(part), parse_mode="HTML")
#             except Exception as e:
#                 await bot.send_message("68086662", str(e))


ARTICLES_FILE = "links.txt"
NEWS_FILE = "links_news.txt"
SENT_ART_FILE = "sent_articles.txt"
SENT_NEWS_FILE = "sent_news.txt"

def _read_archive(path):
    """Читает архив: строки вида 'Title — https://link' -> [(title, link), ...]."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if " — " not in line:
                continue
            title, link = line.rsplit(" — ", 1)
            title = title.strip().strip("[]").strip()
            link = link.strip()
            if title and link:
                out.append((title, link))
    # уберём дубли по ссылке (оставляя первый заголовок)
    seen = set()
    uniq = []
    for t, l in out:
        if l not in seen:
            uniq.append((t, l))
            seen.add(l)
    return uniq

def _read_sent_set(path: str) -> set[str]:
    """Читает историю отправленных ссылок (по ссылке)."""
    if not os.path.exists(path):
        return set()
    sent = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if " — " in line:
                _, link = line.rsplit(" — ", 1)
                sent.add(link.strip())
    return sent

def _append_sent(path: str, chosen: list[tuple[str, str]]) -> None:
    """Добавляет выбранные (title, link) в историю отправленных."""
    if not chosen:
        return
    with open(path, "a", encoding="utf-8") as f:
        for title, link in chosen:
            f.write(f"{title} — {link}\n")

def _source_from_url(link: str) -> str:
    host = urlparse(link).netloc.lower()
    if "vc.ru" in host:       return "VC"
    if "habr.com" in host:    return "Habr"
    if "sostav.ru" in host:   return "Sostav"
    if "dsgners.ru" in host:  return "Dsgners"
    return host or "web"

def _pick_random_without_repeats(archive_path: str, sent_path: str, n: int) -> list[tuple[str, str, str]]:
    """
    Берём из архива N случайных (title, link, source), которых нет в истории.
    Если unseen < N — вернём сколько есть (повторов не будет).
    """
    all_items = _read_archive(archive_path)
    sent = _read_sent_set(sent_path)
    unseen = [(t, l) for (t, l) in all_items if l not in sent]

    if not unseen:
        return []

    if len(unseen) > n:
        unseen = random.sample(unseen, n)

    # добавим источник
    return [(t, l, _source_from_url(l)) for (t, l) in unseen]


def _safe_remove(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        # не падаем из-за файловой ошибки
        pass

# ---------- сбор дайджеста ----------
def build_daily_digest(n_each: int = 5) -> tuple[str, list[tuple[str,str]], list[tuple[str,str]]]:
    """
    Возвращает:
      - готовый HTML-текст,
      - список выбранных статей [(title, link), ...],
      - список выбранных новостей [(title, link), ...]
    Эти списки нужны, чтобы записать их в историю отправленных ПОСЛЕ успешной отправки.
    """
    arts  = _pick_random_without_repeats(ARTICLES_FILE, SENT_ART_FILE, n_each)
    news  = _pick_random_without_repeats(NEWS_FILE,     SENT_NEWS_FILE, n_each)

    parts = []
    parts.append("✏️ <b>Статьи</b>\n")
    if arts:
        for i, (title, link, source) in enumerate(arts, 1):
            parts.append(f'{i}. <a href="{link}">{title}</a> — {source}')
    else:
        parts.append("Новых статей пока нет.")

    parts.append("\n\n📰 <b>Новости</b>\n")
    if news:
        for i, (title, link, source) in enumerate(news, 1):
            parts.append(f'{i}. <a href="{link}">{title}</a> — {source}')
    else:
        parts.append("Новых новостей пока нет.")

    html = "\n".join(parts)
    html += "\n\n#DigitalDigest"
    # вернём пары без source, чтобы писать в историю
    chosen_articles = [(t, l) for (t, l, _) in arts]
    chosen_news = [(t, l) for (t, l, _) in news]
    return html, chosen_articles, chosen_news

# ---------- ежедневная задача ----------
async def send_daily_digest(bot, chat_ids, n_each=5):
    """
    1) обновляем архивы парсером (твои функции), чтобы пополнялись links*.txt
    2) собираем дайджест без повторов
    3) шлём всем chat_ids
    4) при успехе дописываем отправленные ссылки в историю
    """
    try:
        await fetch_sostav()
        await fetch_vc()
        await fetch_habr()
        await fetch_dsgners(articles=True)
        await fetch_dsgners(articles=False)
    except Exception:
        # если парсинг упал — всё равно попробуем собрать из уже накопленных файлов
        pass

    html, chosen_articles, chosen_news = build_daily_digest(n_each=n_each)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(BASE_DIR, "bot_cover.png")
    print(image_path)

    for chat_id in chat_ids:
        try:
            if os.path.exists(image_path):
                photo = FSInputFile(image_path)
                await bot.send_photo(
                    chat_id,
                    photo=photo,
                    caption=html,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(chat_id, html, parse_mode="HTML", disable_web_page_preview=True)

        except Exception as e:
            await bot.send_message("68086662", str(e))
            continue

    # 4) фиксируем «уже отправленные», чтобы не повторять в будущем
    _append_sent(SENT_ART_FILE, chosen_articles)
    _append_sent(SENT_NEWS_FILE, chosen_news)

    _safe_remove(ARTICLES_FILE)
    _safe_remove(NEWS_FILE)


async def daily_digest_job(n_each: int = 5):
    """
    Достаёт chat_ids из БД и шлёт дайджест без повторов.
    """
    try:
        rows = await all_users()  # ожидается список dict с ключом "telegram_id"
        # Соберём уникальные и валидные chat_id
        chat_ids = []
        seen = set()
        for r in rows:
            tid = r.get("telegram_id")
            if not tid:
                continue
            # в твоём коде местами строки — приведём к int/str, Телеграм терпит оба
            tid_str = str(tid).strip()
            if not tid_str or tid_str in seen:
                continue
            seen.add(tid_str)
            chat_ids.append(tid_str)

        if not chat_ids:
            return
        await send_daily_digest(bot, chat_ids, n_each=n_each)
    except Exception as e:
        print(e)
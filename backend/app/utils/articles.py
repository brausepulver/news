import newspaper
from newspaper.google_news import GoogleNewsSource
from database import database
import asyncio
from utils.ai import embed_query
import json
from datetime import datetime, timedelta
from utils.ai import generate_report


def get_article_urls(keywords: list, period: str = "1d", max_results=50, start_date: datetime = None, end_date: datetime = None):
    if start_date and end_date:
        source = GoogleNewsSource(country="US", period=period, max_results=max_results, start_date=start_date, end_date=end_date)
    else:
        source = GoogleNewsSource(country="US", period=period, max_results=max_results)

    article_urls = []

    for keyword in keywords:
        source.build(top_news=False, keyword=keyword)
        urls = source.article_urls()
        article_urls.extend([(url, keyword) for url in urls])

    return article_urls


def get_article(url: str):
    try:
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        config = newspaper.Config()
        config.browser_user_agent = user_agent
        article = newspaper.Article(url, config=config)
        article.download()
        article.parse()
    except Exception as e:
        # print(e)
        return None

    return article


def shape_article(article: newspaper.Article, keyword: str):
    return {
        "url": article.url,
        "title": article.title,
        "date": article.publish_date.replace(tzinfo=None) if article.publish_date else None,
        "content": article.text,
        "keyword": keyword
    }


async def fetch_and_insert_articles(user: dict, max_results=50, start_date: datetime = None, end_date: datetime = None, stop_event: asyncio.Event = None):
    keywords = user["preference_keywords"] or []
    article_urls = get_article_urls(keywords, max_results=max_results, start_date=start_date, end_date=end_date)

    existing_urls = await database.fetch_all(
        "SELECT url FROM articles WHERE url = ANY(:urls)",
        {"urls": [url for url, _ in article_urls]}
    )
    existing_urls_set = {row['url'] for row in existing_urls}
    new_article_urls = [(url, keyword) for url, keyword in article_urls if url not in existing_urls_set]

    print(f"Found {len(new_article_urls)} articles for user {user['id']}")

    for url, keyword in new_article_urls:
        if stop_event and stop_event.is_set():
            return

        article = get_article(url)

        if article:
            shaped_article = shape_article(article, keyword)
            if not (shaped_article["date"] and shaped_article["content"]): continue
            title_embedding = embed_query(shaped_article["title"]) # TODO: Batch
            values = shaped_article | { "title_embedding": json.dumps(title_embedding) }

            await database.execute("""
                INSERT INTO articles (url, title, date, content, title_embedding, keyword)
                VALUES (:url, :title, :date, :content, :title_embedding, :keyword)
                ON CONFLICT DO NOTHING;
            """, values)


async def generate_reports_for_past_week(user: dict, stop_event: asyncio.Event = None):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    await fetch_and_insert_articles(user, max_results=20, start_date=start_date, end_date=end_date, stop_event=stop_event)

    for i in range(7):
        if stop_event and stop_event.is_set():
            return

        report_date = end_date - timedelta(days=i)
        report_exists = await database.fetch_one("SELECT id FROM reports WHERE user_id = :user_id AND DATE(date) = :report_date", {"user_id": user["id"], "report_date": report_date})

        if not report_exists:
            await generate_report(user, i)

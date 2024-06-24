import newspaper
from newspaper.google_news import GoogleNewsSource
import datetime
from database import database
import asyncio
from utils.ai import embed_query
import json


def get_article_urls(keywords: list, period: str = "1d", start_date: datetime = None, end_date: datetime = None):
    if start_date and end_date:
        source = GoogleNewsSource(country="US", period=period, max_results=50, start_date=start_date, end_date=end_date)
    else:
        source = GoogleNewsSource(country="US", period=period, max_results=50)

    article_urls = []

    for keyword in keywords:
        source.build(top_news = False, keyword=keyword)
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


async def fetch_and_insert_articles(user: dict, stop_event: asyncio.Event = None):
    keywords = user["preference_keywords"] or []
    article_urls = get_article_urls(keywords)
    print(f"Found {len(article_urls)} articles for user {user['id']}")

    for url, keyword in article_urls:
        if stop_event and stop_event.is_set():
            return

        article_exists = await database.fetch_one("SELECT 1 FROM articles WHERE url = :url", { "url": url })
        if article_exists:
            continue

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

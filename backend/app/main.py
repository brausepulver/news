# main.py

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager
from routers import reports
from database import database, initialize_database, tables_exist
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from news_utils.articles import get_article_urls, get_article, shape_article

async def fetch_and_insert_articles():
    user_id = 1  # Use user ID 1 for now
    user = await database.fetch_one("SELECT * FROM \"user\" WHERE id = :user_id", {"user_id": user_id})
    if user:
        keywords = user["preference_keywords"]
        article_urls = get_article_urls(keywords)
        print(f"Found {len(article_urls)} articles for user {user_id}")
        for url in article_urls:
            article = get_article(url)
            if article:
                shaped_article = shape_article(article)
                await database.execute(
                    "INSERT INTO articles (url, title, date, content) VALUES (:url, :title, :date, :content) ON CONFLICT DO NOTHING",
                    shaped_article
                )

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    if not await tables_exist(database):
        await initialize_database(database)

    await fetch_and_insert_articles()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_and_insert_articles, 'cron', hour='*/6')
    scheduler.start()

    yield

    scheduler.shutdown()
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

app.include_router(reports.router)

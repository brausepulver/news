from dotenv import load_dotenv
load_dotenv()

import asyncio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from routers import reports, preference
from database import database, initialize_database, tables_exist
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.articles import fetch_and_insert_articles
from routers.reports import user

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    if not await tables_exist(database):
        await initialize_database(database)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: fetch_and_insert_articles(user=Depends(user)), 'cron', hour='*/6')
    scheduler.start()

    stop_event = asyncio.Event()
    articles_task = asyncio.create_task(fetch_and_insert_articles(await user(), stop_event))

    yield

    stop_event.set()
    await articles_task

    scheduler.shutdown()
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins, modify as needed
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods, modify as needed
    allow_headers=["*"],  # Allow all headers, modify as needed
)

app.include_router(reports.router)
app.include_router(preference.router)

from dotenv import load_dotenv
load_dotenv()

import asyncio
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from routers import reports, preference
from database import database, initialize_database, tables_exist
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.articles import fetch_and_insert_articles
from routers.reports import user
import httpx
import os

OPENAI_TTS_API_URL = "https://api.openai.com/v1/audio/speech"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    if not await tables_exist(database):
        await initialize_database(database)

    # scheduler = AsyncIOScheduler()
    # scheduler.add_job(lambda: fetch_and_insert_articles(user=Depends(user)), 'cron', hour='*/6')
    # scheduler.start()

    # stop_event = asyncio.Event()
    # articles_task = asyncio.create_task(fetch_and_insert_articles(await user(), stop_event))

    yield

    # stop_event.set()
    # await articles_task

    # scheduler.shutdown()
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

@app.post("/generate-tts")
async def generate_tts(request: Request):
    request_json = await request.json()
    text = request_json.get("text")

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "tts-1",
        "input": text,
        "voice": "alloy",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(OPENAI_TTS_API_URL, json=data, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    return Response(content=await response.aread(), media_type="audio/mpeg")

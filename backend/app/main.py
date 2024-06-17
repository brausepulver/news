from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager
from routers import reports
from database import database, initialize_database, tables_exist

@asynccontextmanager
async def lifespan(_: FastAPI):
    await database.connect()
    if not await tables_exist(database):
        await initialize_database(database)
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

app.include_router(reports.router)

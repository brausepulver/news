from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from routers import articles
from database import database, initialize_database, tables_exist

app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()
    if not await tables_exist(database):
        await initialize_database(database)

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

app.include_router(articles.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

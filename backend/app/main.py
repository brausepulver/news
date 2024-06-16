from fastapi import FastAPI
from .database import database
from .routers import articles

app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

app.include_router(articles.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

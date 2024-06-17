from fastapi import APIRouter, Depends
from database import database
from routers.reports import user
from utils.articles import embed_query
from models import Preference
import json


router = APIRouter()


@router.get("/preference")
async def get_preference(user: dict = Depends(user)):
    return user["preference_text"]


@router.put("/preference")
async def update_preference(preference: Preference, user: dict = Depends(user)):
    text = preference.preference
    embedding = embed_query(text)
    await database.execute("UPDATE \"user\" SET preference_text = :preference, preference_embedding = :embedding WHERE id = :user_id", {"preference": text, "embedding": json.dumps(embedding), "user_id": user["id"]})
    return preference

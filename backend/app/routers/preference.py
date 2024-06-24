from fastapi import APIRouter, Depends, HTTPException
from database import database
from routers.reports import user
from utils.articles import embed_query
from utils.ai import keyword_chain
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

    # Generate keywords
    keywords = keyword_chain.invoke({"preference_text": text})
    keyword_list = [keyword.strip() for keyword in keywords.split('\n') if keyword.strip()]

    # Update user preference and keywords in database
    query = """
    UPDATE "user"
    SET preference_text = :preference,
        preference_embedding = :embedding,
        preference_keywords = :keywords
    WHERE id = :user_id
    """
    values = {
        "preference": text,
        "embedding": json.dumps(embedding),
        "keywords": keyword_list,  # Send as a list, not a JSON string
        "user_id": user["id"]
    }

    try:
        await database.execute(query, values)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"message": "Preference updated successfully", "keywords": keyword_list}

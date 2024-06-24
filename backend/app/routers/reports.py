from fastapi import APIRouter, Depends, HTTPException, status
from datetime import date
from database import database
from models import Report
from utils.ai import generate_report_v2
from typing import List, Dict, Any


router = APIRouter()


async def user():
    return await database.fetch_one("SELECT * FROM \"user\" WHERE id = :user_id", {"user_id": 1})


@router.post("/reports/today/create")
async def create_report(user: dict = Depends(user)):
    await generate_report_v2(user)

@router.get("/reports/today")
async def get_todays_report(user: dict = Depends(user)):
    user_id = user['id']

    query = """
        SELECT r.id, r.created_at, r.text, r.article_ids,
               a.id as article_id, a.url, a.title, a.date, a.summary
        FROM (
            SELECT * FROM reports
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 1
        ) r
        LEFT JOIN LATERAL unnest(r.article_ids) WITH ORDINALITY AS t(article_id, ord)
            ON TRUE
        LEFT JOIN articles a ON t.article_id = a.id
        ORDER BY t.ord
    """
    values = {
        "user_id": user_id
    }

    rows = await database.fetch_all(query=query, values=values)

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No report found for today")

    articles: List[Dict[str, Any]] = []

    for row in rows:
        if row["article_id"]:
            articles.append({
                "id": row["article_id"],
                "url": row["url"],
                "title": row["title"],
                "date": row["date"],
                "summary": row["summary"]
            })

    report = {
        "id": rows[0]["id"],
        "created_at": rows[0]["created_at"],
        "text": rows[0]["text"],
        "articles": articles
    }

    return report

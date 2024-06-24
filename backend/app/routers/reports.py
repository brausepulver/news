from fastapi import APIRouter, Depends, HTTPException, status
from datetime import date, datetime, timedelta
from database import database
from models import Report
from utils.ai import generate_report
from typing import List, Dict, Any

router = APIRouter()

async def user():
    return await database.fetch_one("SELECT * FROM \"user\" WHERE id = :user_id", {"user_id": 1})

@router.post("/reports/today/create")
async def create_report(user: dict = Depends(user)):
    await generate_report(user)

@router.get("/reports/dates")
async def get_report_dates(user: dict = Depends(user)):
    user_id = user['id']
    query = """
    SELECT DISTINCT DATE(created_at) as report_date
    FROM reports
    WHERE user_id = :user_id
    ORDER BY report_date DESC
    """
    rows = await database.fetch_all(query=query, values={"user_id": user_id})
    return [row['report_date'].isoformat() for row in rows]

@router.get("/reports/{date}")
async def get_report(date: str, user: dict = Depends(user)):
    user_id = user['id']
    try:
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    query = """
        SELECT r.id, r.created_at, r.text, r.article_ids,
               a.id as article_id, a.url, a.title, a.date, a.summary
        FROM reports r
        LEFT JOIN LATERAL unnest(r.article_ids) WITH ORDINALITY AS t(article_id, ord)
            ON TRUE
        LEFT JOIN articles a ON t.article_id = a.id
        WHERE r.user_id = :user_id AND DATE(r.created_at) = :report_date
        ORDER BY r.created_at DESC, t.ord
        LIMIT 1
    """
    values = {
        "user_id": user_id,
        "report_date": report_date
    }

    rows = await database.fetch_all(query=query, values=values)

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No report found for the specified date")

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
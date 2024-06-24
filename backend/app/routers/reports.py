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

    # First, fetch the report
    report_query = """
        SELECT id, created_at, text, article_ids, date
        FROM reports
        WHERE user_id = :user_id AND DATE(date) = :report_date
        ORDER BY created_at DESC
        LIMIT 1
    """
    report_values = {
        "user_id": user_id,
        "report_date": report_date
    }
    report_row = await database.fetch_one(query=report_query, values=report_values)

    if not report_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No report found for the specified date")

    # Then, fetch the articles
    articles_query = """
        SELECT id, url, title, date, summary
        FROM articles
        WHERE id = ANY(:article_ids)
    """
    articles_values = {
        "article_ids": report_row["article_ids"]
    }
    article_rows = await database.fetch_all(query=articles_query, values=articles_values)

    articles = [
        {
            "id": row["id"],
            "url": row["url"],
            "title": row["title"],
            "date": row["date"],
            "summary": row["summary"]
        }
        for row in article_rows
    ]

    report = {
        "id": report_row["id"],
        "created_at": report_row["created_at"],
        "text": report_row["text"],
        "articles": articles,
        "date": report_row["date"]
    }

    return report



@router.post("/reports/{date}/create")
async def create_report(date: str, user: dict = Depends(user)):
    day_offset = (datetime.now().date() - datetime.strptime(date, "%Y-%m-%d").date()).days
    print(day_offset)
    await generate_report(user, day_offset)

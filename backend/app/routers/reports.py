from fastapi import APIRouter, Depends, HTTPException, status
from datetime import date
from database import database
from models import Report
from utils.ai import generate_report


router = APIRouter()


async def user():
    return {"id": 1, "email": "admin@example.com"}


@router.post("/reports/today/create")
async def create_report(user: dict = Depends(user)):
    await generate_report(user, date.today())


@router.get("/reports/today")
async def get_todays_report(user: dict = Depends(user)):
    user_id = user['id']

    query = f"""
        SELECT r.created_at, rs.id as section_id, rs.content, rs.article_id,
               a.id as article_id, a.url, a.title, a.date, a.summary,
               s.id as source_id, s.name as source_name, s.url as source_url, s.favicon as source_favicon
        FROM (
            SELECT * FROM reports
            WHERE user_id = :user_id AND DATE(created_at) = :today
            ORDER BY created_at DESC
            LIMIT 1
        ) r
        LEFT JOIN report_sections rs ON r.id = rs.report_id
        LEFT JOIN articles a ON rs.article_id = a.id
        LEFT JOIN sources s ON a.source_id = s.id
    """
    values = {
        "user_id": user_id,
        "today": date.today()
    }

    rows = await database.fetch_all(query=query, values=values)

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    report = {
        "created_at": rows[0]["created_at"],
        "sections": [
            {
                "id": row["section_id"],
                "content": row["content"],
                "article": {
                    "id": row["article_id"],
                    "url": row["url"],
                    "title": row["title"],
                    "date": row["date"],
                    "summary": row["summary"],
                    "source": {
                        "id": row["source_id"],
                        "name": row["source_name"],
                        "url": row["source_url"],
                        "favicon": row["source_favicon"]
                    }
                } if row["article_id"] else None
            } for row in rows
        ]
    }

    return report

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class Source(BaseModel):
    id: int
    name: str
    url: str
    favicon: Optional[str] = None


class Article(BaseModel):
    id: int
    url: str
    title: str
    date: datetime
    summary: str
    source: Source


class ReportSection(BaseModel):
    id: int
    content: str
    article: Optional[Article] = None


class Report(BaseModel):
    created_at: datetime
    sections: List[ReportSection]


class Preference(BaseModel):
    preference: str

from pydantic import BaseModel

class Item(BaseModel):
    id: int
    title: str
    url: str
    content: str = None
    summary: str = None

from fastapi import APIRouter

router = APIRouter()

@router.get("/articles/{article_id}")
def read_article(article_id: int):
    return {"article_id": article_id, "name": f"Article {article_id}"}

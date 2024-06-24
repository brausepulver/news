import json
import os
from fastapi import HTTPException, status
from datetime import datetime, timedelta

import numpy as np
from database import database
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser

from langchain_nvidia_ai_endpoints import ChatNVIDIA


report_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    Date: {date_formatted}

    Generate a personalised report using the information from the provided articles. This will be shown to the user as his daily brief of the current news.

    You will be provided with the articles in form summaries with the following format:

    ID: {{unique identifier for the article}}
    Title: {{title of the article}}
    Text: {{summary of the article}}

    All text in your personalised report should be enclosed in <context id="article id goes here"></context> html tags, we want to be able to link each section of the report back to the corresponding source. ONLY use <context> tags, they are the only tags my code knows how to parse. The context tags can contain as little or as much text as you'd like, as long as it correctly links back to the source. The most important thing is to correctly segment the text into <context> chunks with the correct source id. I REPEAT: the main thing you should focus on is to get the context linking correct! Each piece of enclosed text MUST link to the CORRECT article.

    Begin the report with a brief summary outlining all the topics covered and then follow it up with a more thorough description of the events. Use a reporting style, do NOT use we/I/you. Make the report around a page in length. The summary almost always looks like very SMALL <context> chunks (sometimes as small as a word!), each linking to the corresponding article. Do your absolute best to combine information from all the article into nice free-flowing text. Start immediately with the report. Do NOT greet the user or anything like this.
    """),
    ("user", "Here are the articles:\n\n{articles_formatted}"),
])
keyword_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    Please generate a list of keywords  for the provided text. The text will be the user's news preferences and the keywords will be used to search and filter news based on those preferences. The keywords must be in the following format:

    keyword_1
    keyword_2
    ...
    The provided articles might be quite similar. Pick those that are different, include all unique types of articles. Do NOT only pick one. In other words, they should be one per line. Immediately start with the keywords and include nothing else. Write around 5 very specific keywords that best (individually!) encapsulate the multitude of the user's interests. Use spaces, never _.
    """),
    ("user", "Here is the user preference text:\n\n{preference_text}")
])

# chat_model = ChatNVIDIA(model=os.environ.get("CHAT_MODEL", "meta/llama3-70b-instruct"))
chat_model = ChatOpenAI(model=os.environ.get('CHAT_MODEL', "gpt-4o"))
embeddings_model = OpenAIEmbeddings(
    model=os.environ.get("EMBEDDINGS_MODEL", "text-embedding-3-large"),
    dimensions=int(os.environ.get("EMBEDDINGS_SIZE", 1024))
)

parser = StrOutputParser()

chain = report_prompt | chat_model | parser
keyword_chain = keyword_prompt | chat_model | parser


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def mmr(candidate_embeddings, candidate_ids, query_embedding, lambda_param, k):
    unselected = set(candidate_ids)
    selected = []

    while len(selected) < k and unselected:
        relevance_scores = {
            doc_id: cosine_similarity(query_embedding, candidate_embeddings[candidate_ids.index(doc_id)])
            for doc_id in unselected
        }

        if not selected:
            best_doc = max(relevance_scores.items(), key=lambda x: x[1])[0]
        else:
            def mmr_score(doc_id):
                relevance = relevance_scores[doc_id]
                diversity = min(
                    1 - cosine_similarity(
                        candidate_embeddings[candidate_ids.index(doc_id)],
                        candidate_embeddings[candidate_ids.index(selected_id)]
                    )
                    for selected_id in selected
                )
                return lambda_param * relevance + (1 - lambda_param) * diversity

            best_doc = max(unselected, key=mmr_score)

        selected.append(best_doc)
        unselected.remove(best_doc)

    return selected


async def get_todays_articles(user, day_offset=0, max_articles=5, lambda_param=0.8):
    target_date = datetime.now().date() - timedelta(days=day_offset)
    query = """
        SELECT id, url, title, date, summary, title_embedding, keyword
        FROM articles
        WHERE DATE(date) BETWEEN DATE(:target_date) - INTERVAL '1 day' AND DATE(:target_date)
        ORDER BY title_embedding <-> :preference_embedding
        LIMIT 1000
    """
    articles = await database.fetch_all(query, {
        "target_date": target_date,
        "preference_embedding": user['preference_embedding']
    })

    if not articles:
        return []

    candidate_embeddings = [np.array(json.loads(article['title_embedding']), dtype=np.float32) for article in articles]
    candidate_ids = [article['id'] for article in articles]
    query_embedding = np.array(json.loads(user['preference_embedding']), dtype=np.float32)

    selected_ids = mmr(candidate_embeddings, candidate_ids, query_embedding, lambda_param, max_articles)

    selected_articles = [next(article for article in articles if article['id'] == id) for id in selected_ids]

    return selected_articles


async def generate_report(user: dict, day_offset: int = 0):
    date = datetime.now().date() - timedelta(days=day_offset)
    articles = await get_todays_articles(user)
    if not articles:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    date_formatted = date.strftime('%Y-%m-%d')
    articles_formatted = "\n\n".join([
        f"ID: {index}\nTitle: {article['title']}\nText: {article['summary']}"
        for index, article in enumerate(articles)
    ])

    response = chain.invoke({ 'date_formatted': date_formatted, 'articles_formatted': articles_formatted })

    query = """
        INSERT INTO reports (user_id, created_at, text, article_ids)
        VALUES (:user_id, :created_at, :text, :article_ids)
        RETURNING id
    """
    values = {
        "user_id": user['id'],
        "created_at": datetime.now(),
        "text": response,
        "article_ids": [article['id'] for article in articles]
    }
    report_id = await database.execute(query, values)
    return report_id


async def parse_generated_report(report_text: str):
    import re

    sections = []
    context_pattern = re.compile(r'<context id="(\d+)">(.*?)</context>', re.DOTALL)
    contexts = context_pattern.findall(report_text)

    for i, (article_id, content) in enumerate(contexts):
        sections.append({
            "id": i + 1,
            "content": content,
            "article_id": int(article_id)
        })

    return {
        "created_at": datetime.now(),
        "sections": sections
    }


def embed_query(query: str):
    return embeddings_model.embed_query(query)

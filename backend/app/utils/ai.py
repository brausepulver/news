import json
import os
from fastapi import HTTPException, status
from datetime import datetime, timedelta

import numpy as np
from database import database
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from operator import itemgetter

from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings


def get_chat_model(env_name: str, default: str):
    name = os.environ.get(env_name, default)
    Model = ChatOpenAI if name.startswith('gpt') else ChatNVIDIA
    return Model(model=name)


summarization_model = get_chat_model('SUMMARIZATION_MODEL', 'gpt-3.5-turbo')
report_model = get_chat_model('REPORT_MODEL', 'gpt-4o')

embeddings_model_name = os.environ.get("EMBEDDINGS_MODEL", "text-embedding-3-large")
# embeddings_model = NVIDIAEmbeddings(model=embeddings_model_name, dimensions=int(os.environ.get("EMBEDDINGS_SIZE", 1024)))
embeddings_model = OpenAIEmbeddings(model=embeddings_model_name, dimensions=int(os.environ.get("EMBEDDINGS_SIZE", 1024)))


report_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    Date: {date_formatted}

    Generate a personalised report using the information from the provided articles. This will be shown to the user as his daily brief of the current news.

    You will be provided with the articles in form summaries with the following format:

    ID: {{unique identifier for the article}}
    Title: {{title of the article}}
    Text: {{summary of the article}}

    All text in your personalised report should be enclosed in <context id="article id goes here"></context> html tags, we want to be able to link each section of the report back to the corresponding source. ONLY use <context> tags, they are the only tags my code knows how to parse. The context tags can contain as little or as much text as you'd like, as long as it correctly links back to the source. The most important thing is to correctly segment the text into <context> chunks with the correct source id. I REPEAT: the main thing you should focus on is to get the context linking correct! Each piece of enclosed text MUST link to the CORRECT article.

    Begin the report with a brief summary outlining all the topics covered and then follow it up with a more thorough description of the events. Use a reporting style, do NOT use we/I/you. Make the report around a page in length. The summary almost always looks like very SMALL <context> chunks (sometimes as small as a word!), each linking to the corresponding article. Do your absolute best to combine information from all the article into nice free-flowing text. Start immediately with the report. Do NOT greet the user or use any other tags (IMPORTANT!).
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

summarize_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a highly skilled article summarizer. Your task is to create concise summaries of news articles while retaining the most important information."),
    ("human", "Please summarize the following article:\n\nTitle: {title}\n\nContent: {content}\n\nProvide a summary that captures all the main points."),
])

parser = StrOutputParser()

summarize_chain = summarize_prompt | summarization_model | parser

report_chain = report_prompt | report_model | parser

def format_articles(articles):
    return "\n\n".join([
        f"ID: {index}\nTitle: {article['title']}\nText: {article['summary']}"
        for index, article in enumerate(articles)
    ])

def selective_summarize(article):
    if article['summary']:
        return article
    else:
        summary = summarize_chain.invoke({"title": article['title'], "content": article['content']})
        return {**article, "summary": summary}

main_chain = (
    RunnablePassthrough.assign(
        articles_summarized=itemgetter("articles") | RunnablePassthrough.map(RunnableLambda(selective_summarize))
    )
    | RunnablePassthrough.assign(
        date_formatted=lambda x: x["date"].strftime("%Y-%m-%d"),
        articles_formatted=lambda x: format_articles(x["articles_summarized"])
    )
    | RunnablePassthrough.assign(
        report=report_chain
    )
)

keyword_chain = keyword_prompt | report_model | parser


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
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())

    query = """
        SELECT id, url, title, date, summary, content, title_embedding, keyword
        FROM articles
        WHERE date >= :start_of_day AND date < :end_of_day
        ORDER BY title_embedding <-> :preference_embedding
        LIMIT 1000
    """
    articles = await database.fetch_all(query, {
        "start_of_day": start_of_day,
        "end_of_day": end_of_day,
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
    articles = await get_todays_articles(user, day_offset=day_offset, max_articles=8)
    if not articles:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    result = main_chain.invoke({ 'date': date, 'articles': [dict(article) for article in articles] })

    articles_summarized = result["articles_summarized"]
    articles_to_update = [articles_summarized[i] for i in range(len(articles)) if not articles[i]['summary']]
    await database.execute_many("UPDATE articles SET summary = :summary WHERE id = :id", [{'summary': article['summary'], 'id': article['id']} for article in articles_to_update])

    report = result["report"]
    query = """
        INSERT INTO reports (user_id, created_at, text, article_ids, date)
        VALUES (:user_id, :created_at, :text, :article_ids, :date)
        RETURNING id
    """
    values = {
        "user_id": user['id'],
        "created_at": datetime.now(),
        "text": report,
        "article_ids": [article['id'] for article in articles],
        "date": date
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

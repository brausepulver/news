import os
from fastapi import HTTPException, status
from datetime import datetime
from database import database
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser


report_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    Date: {date_formatted}

    Generate a personalised report using the information from the provided articles. This will be shown to the user as his daily brief of the current news.

    You will be provided with the articles in form summaries with the following format:

    ID: {{unique identifier for the article}}
    Title: {{title of the article}}
    Text: {{summary of the article}}

    All text in your personalised report should be enclosed in <context id="source id goes here"></context> html tags, we want to be able to link each section of the report back to the corresponding source. ONLY use <context> tags, they are the only tags my code knows how to parse. The context tags can contain as little or as much text as you'd like, as long as it correctly links back to the source. The most important thing is to correctly segment the text into <context> chunks with the correct source id. I REPEAT: the main thing you should focus on is to get the context linking correct! Each piece of enclosed text MUST link to the CORRECT article.

    Begin the report with a brief summary outlining all the topics covered and then follow it up with a more thorough description of the events. The summary almost always looks like very SMALL <context> chunks (sometimes as small as a word!), each linking to the corresponding article. Do your absolute best to combine information from all the article into nice free-flowing text.
    """),
    ("user", "Here are the articles:\n\n{articles_formatted}"),
])
keyword_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    Please generate a list of keywords  for the provided text. The text will be the user's news preferences and the keywords will be used to search and filter news based on those preferences. The keywords must be in the following format:

    keyword_1
    keyword_2
    ...
    In other words, they should be one per line. Immediately start with the keywords and include nothing else. Write around 5 very specific keywords that best (individually!) encapsulate the multitude of the user's interests. Use spaces, never _.
    """),
    ("user", "Here is the user preference text:\n\n{preference_text}")
])

chat_model = ChatOpenAI(model=os.environ.get('CHAT_MODEL', "gpt-4o"))
embeddings_model = OpenAIEmbeddings(
    model=os.environ.get("EMBEDDINGS_MODEL", "text-embedding-3-large"),
    dimensions=int(os.environ.get("EMBEDDINGS_SIZE", 1024))
)

parser = StrOutputParser()

chain = report_prompt | chat_model | parser
keyword_chain = keyword_prompt | chat_model | parser


async def get_todays_articles(database):
    query = """
        SELECT a.id, a.url, a.title, a.date, a.summary
        FROM articles a
        WHERE DATE(a.date) = DATE(NOW())
        LIMIT 10
    """
    return await database.fetch_all(query=query)


async def generate_report(user: dict, date: datetime):
    articles = await get_todays_articles(database)
    if not articles:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    date_formatted = date.strftime('%Y-%m-%d')
    articles_formatted = "\n\n".join([
        f"ID: {article['id']}\nTitle: {article['title']}\nText: {article['summary']}"
        for article in articles
    ])

    response = chain.invoke({ 'date_formatted': date_formatted, 'articles_formatted': articles_formatted })

    report = await parse_generated_report(response)
    await store_report(user, report)


async def generate_keywords(user: dict):
    response = keyword_chain.invoke({ 'preference_text': user['preference_text'] })
    keyword_list = response.split("\n")
    return keyword_list


async def parse_generated_report(report_text: str):
    import re

    sections = []
    context_pattern = re.compile(r'<context id="(\d+)">(.*?)</context>', re.DOTALL)
    contexts = context_pattern.findall(report_text)

    for i, (article_id, content) in enumerate(contexts):
        sections.append({
            "id": i + 1,
            "content": content.strip(),
            "article_id": int(article_id)
        })

    return {
        "created_at": datetime.now(),
        "sections": sections
    }


async def store_report(user, report):
    report_query = """
        INSERT INTO reports (user_id, created_at)
        VALUES (:user_id, :created_at)
        RETURNING id
    """
    report_values = {
        "user_id": user['id'],
        "created_at": report['created_at']
    }

    report_id = await database.execute(report_query, report_values)

    for section in report['sections']:
        section_query = """
            INSERT INTO report_sections (report_id, content, article_id)
            VALUES (:report_id, :content, :article_id)
        """
        section_values = {
            "report_id": report_id,
            "content": section['content'],
            "article_id": section['article_id']
        }
        await database.execute(section_query, section_values)


def embed_query(query: str):
    return embeddings_model.embed_query(query)

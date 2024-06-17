import os
from fastapi import HTTPException, status
from datetime import datetime
from database import database
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
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

model = ChatOpenAI(model=os.environ.get('CHAT_MODEL', "gpt-4o"))

parser = StrOutputParser()

chain = report_prompt | model | parser


async def get_todays_articles(database):
    query = """
        SELECT a.id, a.url, a.title, a.date, a.summary,
               s.id as source_id, s.name as source_name, s.url as source_url, s.favicon as source_favicon
        FROM articles a
        JOIN sources s ON a.source_id = s.id
        WHERE DATE(a.date) = DATE(NOW())
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

    report = await parse_generated_report(response, date)
    await store_report(user, report)


async def parse_generated_report(report_text: str, report_date: datetime):
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
        "created_at": report_date,
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
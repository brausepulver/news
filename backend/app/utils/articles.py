import newspaper
from newspaper.google_news import GoogleNewsSource
import datetime

def get_article_urls(keywords: list, period: str = "1d", start_date: datetime = None, end_date: datetime = None):
    if start_date and end_date:
        source = GoogleNewsSource(country="US", period=period, max_results=100, start_date=start_date, end_date=end_date)
    else:
        source = GoogleNewsSource(country="US", period=period, max_results=100)

    article_urls = []

    for keyword in keywords:
        source.build(top_news = False, keyword=keyword)
        article_urls.extend(source.article_urls())

    return article_urls

def get_article(url: str):
    try:
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        config = newspaper.Config()
        config.browser_user_agent = user_agent
        article = newspaper.Article(url, config=config)
        article.download()
        article.parse()
    except Exception as e:
        # print(e)
        return None

    return article

def shape_article(article: newspaper.Article):
    parsed_date = article.publish_date.strftime("%Y-%m-%d") if article.publish_date else None
    return {
        "url": article.url,
        "title": article.title,
        "date": parsed_date,
        "content": article.text
    }

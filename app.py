import requests
import simplejson as json
from flask import Flask
from sqlalchemy import create_engine
from datetime import datetime
from contextlib import contextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import coloredlogs
import logging
from textblob import TextBlob
from ast import literal_eval


logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG')


sched = BackgroundScheduler()

app = Flask(__name__)


# Helpers
def load_config_settings():
    with open('config.json') as json_data:
        settings = json.load(json_data)
        return settings


# Settings
settings = load_config_settings()
news_api_key = settings["news_api_key"]

newsSources = [
    'associated-press',
    'bbc-news',
    'bloomberg',
    'cnn',
    'google-news',
    'hacker-news',
    'the-new-york-times',
    'the-telegraph',
    'the-wall-street-journal',
    'the-washington-post',
]


# SQL Connection
CONNECTION_STRING = (
    'mysql://' + settings["mysqluser"] + ':' + settings["mysqlpw"] + '@'
    + settings["mysqllocation"] + '/' + settings["database"] +
    '?charset=utf8&use_unicode=0'
)
engine = create_engine(CONNECTION_STRING, pool_recycle=3600)
connection = engine.connect()


def get_news(source, sort, key):
    newsAPIURL = (
        'https://newsapi.org/v1/articles?source=' + source + '&sortBy='
        + sort + '&apiKey=' + key
    )
    try:
        return requests.get(newsAPIURL).content
    except requests.exceptions.RequestException as e:
        logger.Error("Error fetching: {}".format(e))


def get_multisource_news_array(sources, sort):
    json_news_list = []
    logger.info("News source request sent!")
    for source in sources:
        json_news_list.append((
            get_news(
                source,
                sort,
                news_api_key
            )
        ).decode('utf8'))
    return json_news_list


def build_url_list(parsed_json):
    anchor = "<a href={url}>{title}</a>"
    for article in parsed_json:
        yield anchor.format(
            url=(article["url"]).decode('utf8'),
            title=(article["title"]).decode('utf8'),
        )


def format_data(json_content):
    # TODO: return more than just titles
    parsed_json = json.loads(json_content)
    if parsed_json["status"] == "ok":
        lines = "<br/>".join(build_url_list(parsed_json))
        return lines
    return "status == not ok"


@app.route('/')
def hello():
    return "Hello World!"


@contextmanager
def sql_execute(query, *args, **kwargs):
    try:
        result = engine.execute(query, *args, **kwargs)
        logging.info(
            "{query_operation} EXECUTED"
            .format(query_operation=query[:6])
        )
        yield result
    except Exception:
        print("whoops")
        result.close()


@app.route('/unsortedlist')
def list_articles():
    lines = None
    with sql_execute("SELECT * FROM UnsortedArticles") as result:
        list_of_dicts = [
            dict((key, value) for key, value in row.items()) for row in result
        ]
        lines = "<br/>".join(build_url_list(list_of_dicts))
    return lines


def fetch_articles_and_save():
    news_json_array = get_multisource_news_array(newsSources, "top")
    for source in news_json_array:
        source = json.loads(source)
        for article in source["articles"]:
            if article["publishedAt"] is not None:
                ods = article["publishedAt"]
                ods = ods[:19]
                dt = datetime.strptime(ods, "%Y-%m-%dT%H:%M:%S")
                dts = dt.strftime('%Y-%m-%d %H:%M:%S')
                sentiment_tuple = grade_article_title(article["title"])
                with sql_execute(
                    """INSERT INTO UnsortedArticles
                    (author, title, url, imageurl, sentiment, description, publishtime, polarity, subjectivity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    article["author"],
                    article["title"],
                    article["url"],
                    article["urlToImage"],
                    sentiment_tuple,
                    article["description"],
                    dts,
                    sentiment_tuple['polarity'],
                    sentiment_tuple['subjectivity'],
                ):
                    pass
            else:
                with sql_execute(
                    """INSERT INTO UnsortedArticles
                    (author, title, url, imageurl, description)
                    VALUES (%s,%s, %s, %s, %s)""",
                    article["author"],
                    article["title"],
                    article["url"],
                    article["urlToImage"],
                    article["description"]
                ):
                    pass
    return "complete"


def grade_article_title(title):
    blob = TextBlob(title)
    sentiment_dict = {
        "Polarity": blob.sentiment.polarity,
        "Subjectivity": blob.sentiment.subjectivity,
    }
    return sentiment_dict


def add_sentiment_to_article_records():
    with sql_execute(
            "SELECT *\
            FROM UnsortedArticles\
            WHERE Sentiment IS NULL\
            OR Sentiment = ''"
        ) as result:
            list_of_dicts = [
                dict((key, value) for key, value in row.items())
                for row in result
            ]
    if list_of_dicts:
        for article in list_of_dicts:
            if article["sentiment"] is None:
                article["sentiment"] = grade_article_title(
                    article["title"].decode('utf8')
                )
        for article in list_of_dicts:
            print("Article Sentiment: {}".format(article['sentiment']))
            sentiment_string = article['sentiment'].decode('utf8')
            sentiment_dict = literal_eval(sentiment_string)
            with sql_execute(
                "Update UnsortedArticles SET sentiment=\"{}\",\
                polarity={}, subjectivity={}\
                WHERE articleID={}\
                AND(\
                sentiment IS NULL OR\
                polarity IS NULL OR\
                subjectivity IS NULL\
                )".format(
                    article['sentiment'].decode('utf8'),
                    sentiment_dict['Polarity'],
                    sentiment_dict['Subjectivity'],
                    article['articleID'],
                )
            ):
                pass

# Seconds can be replaced with minutes, hours, or days
sched.add_job(fetch_articles_and_save, trigger='cron', day='*', hour='0')
sched.add_job(add_sentiment_to_article_records, trigger='cron', day='*', hour='0', minute='30')
sched.start()


if __name__ == '__main__':
    app.run()

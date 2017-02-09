import requests
import simplejson as json
from flask import Flask
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import and_, or_, not_
from sqlalchemy import text
from datetime import datetime
from contextlib import contextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import coloredlogs
import logging
from textblob import TextBlob
from ast import literal_eval
import psycopg2


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
    "postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}".format(
        user=settings['dbuser'],
        password=settings['dbpw'],
        host=settings["dbhost"],
        port=settings['dbport'],
        db=settings['db'],
    )
)
engine = create_engine(CONNECTION_STRING, pool_recycle=3600)
connection = engine.connect()
meta = MetaData(engine)
articles_table = Table('Articles', meta, autoload=True, autoload_with=engine)
# from ipdb import set_trace; set_trace()
# print("-----------------------------META: {}".format(meta))


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


def build_url_list(row_dict_list):
    anchor = "<a href={url}>{title}</a>"
    for article in row_dict_list:
        yield anchor.format(
            url=(article["url"]),
            title=(article["title"]),
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
    row_list = []
    with engine.connect() as conn:
        select_statement = articles_table.select()
        result_set = conn.execute(select_statement)
        # building a dict that can be manipulated from the result set
        for row in result_set:
            row_dict = dict(row.items())
            row_list.append(row_dict)
    lines = "<br/>".join(build_url_list(row_list))
    return lines

@app.route('/badnews')
def bad_news():
    lines = None
    row_list = []
    with engine.connect() as conn:
        select_statement = articles_table.select().where(
            articles_table.c.polarity < 0
        ).group_by(
            articles_table.c.article_id,
            articles_table.c.title
        ).order_by(
            articles_table.c.time_created.desc(),
            articles_table.c.publish_time.desc()
        )
        result_set = conn.execute(select_statement)
        # building a dict that can be manipulated from the result set
        for row in result_set:
            row_dict = dict(row.items())
            row_list.append(row_dict)
    lines = "<br/>".join(build_url_list(row_list))
    return lines

@app.route('/goodnews')
def good_news():
    lines = None
    # query = (
    #         "SELECT title, url, time_created, publish_time "
    #         "FROM \"Articles\" "
    #         "WHERE polarity > 0.0 and subjectivity < 0.5 "
    #         "GROUP BY title, url "
    #         "ORDER BY time_created DESC, publish_time DESC;"
    #     )
    # with sql_execute(query) as result:
    #     list_of_dicts = [
    #         dict((key, value) for key, value in row.items()) for row in result
    #     ]
    row_list = []
    with engine.connect() as conn:
        select_statement = articles_table.select().where(
            and_(
                articles_table.c.polarity > 0.0,
                articles_table.c.subjectivity < 0.5
            )
        ).group_by(
            articles_table.c.article_id,
            articles_table.c.title,
            articles_table.c.time_created
        ).order_by(
            articles_table.c.time_created.desc(),
            articles_table.c.publish_time.desc()
        )
        result_set = conn.execute(select_statement)
        # building a dict that can be manipulated from the result set
        for row in result_set:
            row_dict = dict(row.items())
            row_list.append(row_dict)
    lines = "<br/>".join(build_url_list(row_list))
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
                with engine.connect() as conn:
                    insert_statement = articles_table.insert().values(
                        author=article["author"],
                        title= article["title"],
                        url= article["url"],
                        url_to_image= article["urlToImage"],
                        sentiment=article["sentiment"],
                        description= article["description"],
                        publish_time= dts,
                        polarity= sentiment_tuple["Polarity"],
                        subjectivity= sentiment_tuple["Subjectivity"]
                    )
                    conn.execute(insert_statement)
            else:
                with engine.connect() as conn:
                    insert_statement = articles_table.insert().values(
                        author=article["author"],
                        title= article["title"],
                        url= article["url"],
                        url_to_image= article["urlToImage"],
                        sentiment=article["sentiment"],
                        description= article["description"],
                        polarity= sentiment_tuple["Polarity"],
                        subjectivity= sentiment_tuple["Subjectivity"]
                    )
                    conn.execute(insert_statement)
    return "complete"


def grade_article_title(title):
    blob = TextBlob(title)
    sentiment_dict = {
        "Polarity": blob.sentiment.polarity,
        "Subjectivity": blob.sentiment.subjectivity,
    }
    return sentiment_dict


def add_sentiment_to_article_records():
    row_list = []
    with engine.connect() as conn:
        select_statement = articles_table.select().where(
            articles_table.c.sentiment == None
        )
        result_set = conn.execute(select_statement)
        # building a dict that can be manipulated from the result set
        for row in result_set:
            row_dict = dict(row.items())
            row_list.append(row_dict)
    if row_list:
        for r in row_list:
            if r['sentiment'] is None or r['sentiment'] == '' :
                sentiment = grade_article_title(r['title'])
                r['sentiment'] = json.dumps(sentiment)
                with engine.connect() as conn:
                    update_statement = articles_table.update().where(
                        articles_table.c.article_id==r['article_id']
                    ).values(
                        sentiment=r['sentiment'],
                        polarity=sentiment['Polarity'],
                        subjectivity=sentiment['Subjectivity']
                    )
                    conn.execute(update_statement)
    else:
        print('No blank sentiment values found')
    print('Sentiment Addition Complete')


# Seconds can be replaced with minutes, hours, or days
sched.add_job(fetch_articles_and_save, trigger='cron', day='*', hour='0')
sched.add_job(add_sentiment_to_article_records, trigger='cron', day='*', hour='0', minute='30')
sched.start()

if __name__ == '__main__':
    app.run()

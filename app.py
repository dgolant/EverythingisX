# Sentiment / ML
from textblob import TextBlob
from pandas import DataFrame
import numpy
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.cross_validation import KFold
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.feature_extraction.text import TfidfTransformer



# operation
from apscheduler.schedulers.background import BackgroundScheduler

# utility
from datetime import datetime
from ast import literal_eval
import simplejson as json

# database creation / manipulation
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import and_, or_, not_, select, join
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from contextlib import contextmanager
from flask_sqlalchemy import SQLAlchemy
import psycopg2

# networking/requests/routing/server
import requests
from flask import Flask
from flask_heroku import Heroku
import coloredlogs
import logging
import os
import sys




logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG')
sched = BackgroundScheduler()
app = Flask(__name__)
app._static_folder = os.path.abspath("static/")
heroku = Heroku(app)
db = SQLAlchemy(app)
NEWLINE = '\n'

# Helpers
def load_config_settings():
    if os.environ.get('is_heroku', None) == None:
        with open('config.json') as json_data:
            settings = json.load(json_data)
            return settings
    else:
        return dict(os.environ)


# Settings
settings = load_config_settings()
news_api_key = settings["news_api_key"]
TRAINING_FILES = [
        {
            'file_name':'positive_headlines.csv',
            'class': 1
        },
        {
            'file_name':'negative_headlines.csv',
            'class': -1
        }
    ]

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

def print_json(json_obj):
    print (
        json.dumps(
            json_obj,
            sort_keys=True,
            indent=4,
            separators=(
                ',',
                ': '
            )
        )
    )


# SQL Connection
CONNECTION_STRING = None
if os.environ.get('is_heroku', None) == None:
    CONNECTION_STRING = (
        "postgresql+psycopg2://"
        "{user}:"
        "{password}@"
        "{host}:"
        "{port}/"
        "{db}".format(
            user=settings['dbuser'],
            password=settings['dbpw'],
            host=settings["dbhost"],
            port=settings['dbport'],
            db=settings['db'],
        )
    )
else:
    CONNECTION_STRING = os.environ.get('DATABASE_URL')


engine = create_engine(CONNECTION_STRING, pool_recycle=3600)

try:
    connection = engine.connect()
except Exception as exc:
    print(
            "Connection is Empty, please start the EverythingIsX AppDB" 
            "ERROR DETAIL: {}".format(exc)
        )
    sys.exit()
meta = MetaData(engine)
articles_table = Table(
    'Articles',
    meta,
    autoload=True,
    autoload_with=engine
)


###############################
#                             #
#       ML RELATED CODE       #
#                             #
###############################


def read_csv(file_name):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path,'resources', file_name)
    print("FILEPATH----------{}".format(file_path))
    if os.path.isfile(file_path):
        lines = []
        f = open(file_path, encoding="latin-1")
        for line in f:
            lines.append(line)
        f.close()
        return lines
    else:
        print("You have supplied an invalid path for your CSV")


def build_data_frame(files):
    rows = []
    index = []
    i = 0
    for file in files:
        for line in read_csv(file['file_name']):
            rows.append({'text': line, 'class': file['class']})
            index.append(i)
            i += 1
    data_frame = DataFrame(rows, index=index)
    return data_frame


def dataframe_from_csv_files(files):
    data = DataFrame({'text' : [], 'class' : [] })
    data = data.append(build_data_frame(files))
    data = data.reindex(numpy.random.permutation(data.index))
    return data


def train_machine_return_pipeline(data_files):
        data = dataframe_from_csv_files(data_files)
        count_vectorizer = CountVectorizer(ngram_range=(1, 7))
        counts = count_vectorizer.fit_transform(data['text'].values)
        classifier = MultinomialNB()
        targets = data['class'].values
        classifier.fit(counts, targets)
        # examples = [
        #     "Pedophile raped baby until she bled "
        #     "and got a slap on the wrist",
        #     "ESPN just released a Video Story about Arthur "
        #     "the stray dog who followed a Swedish extreme sports "
        #     "team along a 430 mile race"
        # ]
        # example_counts = count_vectorizer.transform(examples)
        # predictions = classifier.predict(example_counts)
        pipeline = Pipeline(
            [
                ('vectorizer',  count_vectorizer),
                #('tfidf_transformer',  TfidfTransformer()),
                # Removing above line tunes accuracy, but unclear how
                ('classifier',  classifier)
            ]
        )
        return pipeline, data, count_vectorizer

# This function can be used to validate tuning of the model
def k_fold_crossvalidate(data, pipeline):
    k_fold = KFold(n=len(data), n_folds=6)
    scores = []
    confusion = numpy.array([[0, 0], [0, 0]])
    for train_indices, test_indices in k_fold:
        train_text = data.iloc[train_indices]['text'].values
        train_y = data.iloc[train_indices]['class'].values

        test_text = data.iloc[test_indices]['text'].values
        test_y = data.iloc[test_indices]['class'].values

        pipeline.fit(train_text, train_y)
        predictions = pipeline.predict(test_text)
        print(predictions)
        confusion += confusion_matrix(test_y, predictions)
        score = f1_score(test_y, predictions, pos_label=1)
        scores.append(score)

    print('Total headlines classified:', len(data))
    print('Score:', sum(scores)/len(scores))
    print('Confusion matrix:')
    print(confusion)
    # import ipdb; ipdb.set_trace()


global_pipeline, global_data, global_vectorizer = train_machine_return_pipeline(TRAINING_FILES)
examples = [
    "Pedophile raped baby until she bled "
    "and got a slap on the wrist",
    "ESPN just released a Video Story about Arthur "
    "the stray dog who followed a Swedish extreme sports "
    "team along a 430 mile race"
]
# import ipdb; ipdb.set_trace();
# example_counts = global_vectorizer.transform(examples)
# predictions = global_pipeline.predict(example_counts)
# print("Prediction: {}".format(predictions))
dataTest = dataframe_from_csv_files(TRAINING_FILES)
k_fold_crossvalidate(dataTest, global_pipeline)



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


# Routes
@app.route('/')
def hello():
    return "200 OK"


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


@app.route('/badnewsjson')
def bad_news():
    lines = None
    row_list = []
    with engine.connect() as conn:
        distinct_article_id_table = (
            select(
                [articles_table.c.article_id]
            ).distinct(
                articles_table.c.title
            )
        ).alias('da')
        joined_id_articles_tbl = join(
            articles_table,
            distinct_article_id_table,
            articles_table.c.article_id == distinct_article_id_table.c.article_id
        )
        select_statement = select(
            [
                articles_table.c.article_id,
                articles_table.c.title,
                articles_table.c.author,
                articles_table.c.url,
                articles_table.c.url_to_image,
                articles_table.c.sentiment,
                articles_table.c.description,
                articles_table.c.publish_time,
                articles_table.c.polarity,
                articles_table.c.subjectivity,
                articles_table.c.time_created
            ]
        ).select_from(
            joined_id_articles_tbl
        ).where(
            and_(
                articles_table.c.polarity < -0.1,
                articles_table.c.subjectivity < 0.5,
                articles_table.c.publish_time is not None,
                articles_table.c.publish_time.isnot(None),
                articles_table.c.publish_time != None,
            )
        ).order_by(
            articles_table.c.publish_time.desc(),
            articles_table.c.time_created.desc(),
        )
        result_set = conn.execute(select_statement)
        # building a dict that can be manipulated from the result set
        for row in result_set:
            row_dict = dict(row.items())
            row_list.append(row_dict)
    lines = json.dumps(row_list, indent=4, sort_keys=True, default=str)
    return lines


@app.route('/goodnewsjson')
def good_news():
    lines = None
    row_list = []
    with engine.connect() as conn:
        distinct_article_id_table = (
            select(
                [articles_table.c.article_id]
            ).distinct(
                articles_table.c.title
            )
        ).alias('da')
        joined_id_articles_tbl = join(
            articles_table,
            distinct_article_id_table,
            articles_table.c.article_id == distinct_article_id_table.c.article_id
        )
        select_statement = select(
            [
                articles_table.c.article_id,
                articles_table.c.title,
                articles_table.c.author,
                articles_table.c.url,
                articles_table.c.url_to_image,
                articles_table.c.sentiment,
                articles_table.c.description,
                articles_table.c.publish_time,
                articles_table.c.polarity,
                articles_table.c.subjectivity,
                articles_table.c.time_created
            ]
        ).select_from(
            joined_id_articles_tbl
        ).where(
            and_(
                articles_table.c.polarity > 0.0,
                articles_table.c.subjectivity < 0.5,
                articles_table.c.publish_time is not None,
                articles_table.c.publish_time.isnot(None),
                articles_table.c.publish_time != None,
            )
        ).order_by(
            articles_table.c.publish_time.desc(),
            articles_table.c.time_created.desc(),
        )
        result_set = conn.execute(select_statement)
        # building a dict that can be manipulated from the result set
        for row in result_set:
            row_dict = dict(row.items())
            row_list.append(row_dict)
    lines = json.dumps(row_list, indent=4, sort_keys=True, default=str)
    return lines


@app.route('/goodnews')
def good_news_page():
    root_dir = os.path.dirname(os.getcwd())
    return app.send_static_file(
        'views/goodnews.html'
    )

@app.route('/badnews')
def bad_news_page():
    root_dir = os.path.dirname(os.getcwd())
    return app.send_static_file(
        'views/badnews.html'
    )

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
                        sentiment=json.dumps(sentiment_tuple),
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
                        sentiment=json.dumps(sentiment_tuple),
                        description= article["description"],
                        polarity= sentiment_tuple["Polarity"],
                        subjectivity= sentiment_tuple["Subjectivity"]
                    )
                    conn.execute(insert_statement)
                    print(insert_statement)
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
sched.add_job(
    fetch_articles_and_save,
    trigger='cron',
    day='*',
    hour='0'
)


sched.add_job(
    add_sentiment_to_article_records,
    trigger='cron',
    day='*',
    hour='0',
    minute='30'
)


sched.start()
# global_pipeline = train_machine_return_pipeline(TRAINING_FILES)
# import ipdb; ipdb.set_trace()

if __name__ == '__main__':
    app.run()

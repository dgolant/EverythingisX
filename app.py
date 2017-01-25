import requests
import simplejson as json
from flask import Flask
from sqlalchemy import *  # look into flake8 for linting and library comments
from datetime import datetime
import dateutil.parser
from contextlib import contextmanager
import coloredlogs, logging

logger = logging.getLogger(__name__)
coloredlogs.install(level='INFO')


#Timer stuff, need to validate necessity
from apscheduler.schedulers.background import BackgroundScheduler

sched = BackgroundScheduler()

app = Flask(__name__)

#Helpers
def load_config_settings():
	with open('config.json') as json_data:
		settings = json.load(json_data)
		return settings

#Settings
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

#SQL Connection
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
		json_news_list.append((get_news(source, sort, news_api_key)).decode('utf8'))
	return json_news_list


def build_url_list(parsed_json):
	anchor = "<a href={url}>{title}</a>"
	for article in parsed_json["articles"]:
		yield anchor.format(
			url=article["url"],
			title=article["title"],
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
		logging.info("{query_operation} EXECUTED".format(query_operation=query[:6]))
		yield result
	except Exception:
		result.close()

@app.route('/unsortedlist')
def list_articles():
	lines = None
	with sql_execute("SELECT * FROM UnsortedArticles") as result:
		lines = "<br/>".join.join(build_url_list(result))
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
				with sql_execute("""INSERT INTO UnsortedArticles (author, title, url, imageurl, description, publishtime) VALUES (%s,%s, %s, %s, %s, %s)""", article["author"], article["title"], article["url"], article["urlToImage"], article["description"], dts):
					pass
			else:
				with sql_execute("""INSERT INTO UnsortedArticles (author, title, url, imageurl, description) VALUES (%s,%s, %s, %s, %s)""", article["author"], article["title"], article["url"], article["urlToImage"], article["description"]):
					pass
	return "complete"



# seconds can be replaced with minutes, hours, or days
sched.add_job(fetch_articles_and_save, trigger = 'cron', day = '*', hour = '0')
sched.start()


if __name__ == '__main__':
	app.run()
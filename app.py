import requests
import simplejson as json
from flask import Flask
from sqlalchemy import *
from datetime import datetime
import dateutil.parser

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

newsSources = ['associated-press',
	'bbc-news',
	'bloomberg',
	'cnn',
	'google-news',
	'hacker-news',
	'the-new-york-times',
	'the-telegraph',
	'the-wall-street-journal',
	'the-washington-post'
]

#SQL Connection
CONNECTION_STRING = 'mysql://' + settings["mysqluser"] + ':' + settings["mysqlpw"] + '@' + settings["mysqllocation"] + '/' + settings["database"]+ '?charset=utf8&use_unicode=0'
engine = create_engine(CONNECTION_STRING, pool_recycle=3600)
connection = engine.connect()


def get_news(source, sort, key):
	newsAPIURL = 'https://newsapi.org/v1/articles?source='+source+'&sortBy='+sort+'&apiKey='+key
	r = None
	try:
		r = requests.get(newsAPIURL).content
		return r
	except requests.exceptions.RequestException:
		print("Error fetching")

def get_multisource_news_array(sources, sort):
	jsonNewsList = []
	for source in sources:
		jsonNewsList.append(get_news(source, sort, news_api_key).decode('utf8'))
	return jsonNewsList

def format_data(jsonContent):
	# TODO: return more than just titles
	parsedJson = json.loads(jsonContent)
	if parsedJson["status"] == "ok":
		lines = ""
		for article in parsedJson["articles"]:
			lines += "<a href=" + article["url"] + ">" + article["title"] + "</a>" + "<br/>"
		return lines
	else:
		return "status == not ok"

@app.route('/')
def hello():
    return "Hello World!"

@app.route('/unsortedlist')
def list_articles():
	result = engine.execute("select * from UnsortedArticles")
	lines = ""
	for row in result:
		lines += "<a href=" + row["url"].decode('utf8') + ">" + row["title"].decode('utf8') + "</a>" + "<br/>"
	result.close()
	return lines


def fetch_articles_and_save():
	newsJSONArray = get_multisource_news_array(newsSources, "top")
	for source in newsJSONArray:
		source = json.loads(source)
		for article in source["articles"]:
			if article["publishedAt"] is not None:
				ods = article["publishedAt"]
				ods = ods[:19]
				dt = datetime.strptime(ods, "%Y-%m-%dT%H:%M:%S")
				dts = dt.strftime('%Y-%m-%d %H:%M:%S')
				engine.execute ("""INSERT INTO UnsortedArticles (author, title, url, imageurl, description, publishtime) VALUES (%s,%s, %s, %s, %s, %s)""", article["author"], article["title"], article["url"], article["urlToImage"], article["description"], dts)
			else:
				engine.execute ("""INSERT INTO UnsortedArticles (author, title, url, imageurl, description) VALUES (%s,%s, %s, %s, %s)""", article["author"], article["title"], article["url"], article["urlToImage"], article["description"])
	return "complete"



# seconds can be replaced with minutes, hours, or days
sched.add_job(fetch_articles_and_save, trigger = 'cron', day = '*', hour = 0)
sched.start()


if __name__ == '__main__':
	app.run()
import webapp2
import jinja2
import os
import hashlib
import logging
import time
from datetime import datetime
from django.utils import simplejson

from google.appengine.api import urlfetch
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

## Models ##

class Tweets(db.Model):
	text = db.TextProperty()
	username = db.StringProperty()
	date = db.DateTimeProperty()

## Views ##

class BaseHandler(webapp2.RequestHandler):
	'''Parent class for all handlers'''
	def write(self, content):
		return self.response.out.write(content)

	def rget(self, name):
		'''Gets a HTTP parameter'''
		return self.request.get(name)

	def render(self, template, params={}):
		template = jinja_env.get_template(template)
		self.response.out.write(template.render(params))

	def set_cookie(self, cookie):
		self.response.headers.add_header('Set-Cookie', cookie)

	def delete_cookie(self, cookie):
		self.response.headers.add_header('Set-Cookie', '%s=; Path=/' % cookie)

class MainHandler(BaseHandler):
	def get(self):
		self.render('index.html')

class InitScrapeHandler(BaseHandler):
	def get(self):
		self.write('scraping...')
		initial_scrape()


## The Magic ##

SCRAPE_URL = 'http://search.twitter.com/search.json?q=(%22someone%20should%22)%20(make%20OR%20build%20OR%20create%20OR%20develop%20OR%20start%20OR%20design%20OR%20invent)%20(software%20OR%20app%20OR%20application%20OR%20tool%20OR%20website%20OR%20site%20OR%20service%20OR%20product%20OR%20company%20OR%20business)&page='
js = '{"completed_in":0.099,"max_id":323208999682064387,"max_id_str":"323208999682064387","page":1,"query":"%28%22someone+should%22%29+%28make+OR+build+OR+create+OR+develop+OR+start+OR+design+OR+invent%29+%28software+OR+app+ORapplication+OR+tool+OR+website+OR+site+OR+service+OR+product+OR+company+OR+business%29","refresh_url":"?since_id=323208999682064387&q=%28%22someone%20should%22%29%20%28make%20OR%20build%20OR%20create%20OR%20develop%20OR%20start%20OR%20design%20OR%20invent%29%20%28software%20OR%20app%20ORapplication%20OR%20tool%20OR%20website%20OR%20site%20OR%20service%20OR%20product%20OR%20company%20OR%20business%29","results":[{"created_at":"Sat, 13 Apr 2013 23:00:05 +0000","from_user":"takenji_ebooks","from_user_id":916596266,"from_user_id_str":"916596266","from_user_name":"\u7af9\u4e0bE\u672c","geo":null,"id":323208999682064387,"id_str":"323208999682064387","iso_language_code":"en","metadata":{"result_type":"recent"},"profile_image_url":"http:\/\/a0.twimg.com\/profile_images\/2788368338\/68a4fda1e0c375a54bc2d7ee34b8e24b_normal.jpeg","profile_image_url_https":"https:\/\/si0.twimg.com\/profile_images\/2788368338\/68a4fda1e0c375a54bc2d7ee34b8e24b_normal.jpeg","source":"&lt;a href=&quot;http:\/\/twitter.com\/takenji_ebooks&quot;&gt;Takenji Ebooks&lt;\/a&gt;","text":"Someone should make a #tvtropes-like site for programming, software behavior, and common defects."},{"created_at":"Fri, 12 Apr 2013 12:26:12 +0000","from_user":"gurdeep_kaur1","from_user_id":528391973,"from_user_id_str":"528391973","from_user_name":"gurdeep kaur","geo":null,"id":322687089936302080,"id_str":"322687089936302080","iso_language_code":"en","metadata":{"result_type":"recent"},"profile_image_url":"http:\/\/a0.twimg.com\/profile_images\/3491538694\/724134cbf0db43cb5e0e567111699392_normal.jpeg","profile_image_url_https":"https:\/\/si0.twimg.com\/profile_images\/3491538694\/724134cbf0db43cb5e0e567111699392_normal.jpeg","source":"&lt;a href=&quot;http:\/\/twitter.com\/&quot;&gt;web&lt;\/a&gt;","text":"i reckon someone should make a website\/app where you can see what you would look like as a different gender\/ethnicity"},{"created_at":"Thu, 11 Apr 2013 17:44:45 +0000","from_user":"dujkan","from_user_id":12953402,"from_user_id_str":"12953402","from_user_name":"Christian Zibreg","geo":null,"id":322404868520296448,"id_str":"322404868520296448","iso_language_code":"en","metadata":{"result_type":"recent"},"profile_image_url":"http:\/\/a0.twimg.com\/profile_images\/2656661499\/794874121a14bf6d5a5a0b673b832854_normal.jpeg","profile_image_url_https":"https:\/\/si0.twimg.com\/profile_images\/2656661499\/794874121a14bf6d5a5a0b673b832854_normal.jpeg","source":"&lt;a href=&quot;http:\/\/tapbots.com\/software\/tweetbot\/mac&quot;&gt;Tweetbot for Mac&lt;\/a&gt;","text":"@xxTigerShark someone should start an App Store localization services company or something...","to_user":"xxTigerShark","to_user_id":152058448,"to_user_id_str":"152058448","to_user_name":"Kevin Makens","in_reply_to_status_id":322404710738968576,"in_reply_to_status_id_str":"322404710738968576"},{"created_at":"Mon, 08 Apr 2013 02:54:24 +0000","from_user":"MatthewRobertA","from_user_id":389659496,"from_user_id_str":"389659496","from_user_name":"Matthew Anderson","geo":null,"id":321093641999372288,"id_str":"321093641999372288","iso_language_code":"en","metadata":{"result_type":"recent"},"profile_image_url":"http:\/\/a0.twimg.com\/profile_images\/3283853313\/2051502e877d89d967fd67a9c00aa5bd_normal.jpeg","profile_image_url_https":"https:\/\/si0.twimg.com\/profile_images\/3283853313\/2051502e877d89d967fd67a9c00aa5bd_normal.jpeg","source":"&lt;a href=&quot;http:\/\/twitter.com\/&quot;&gt;web&lt;\/a&gt;","text":"Someone should make web software to make this easier for all publishers... durrrrr.... http:\/\/t.co\/YEd0n0lJNC You may like this, @SeedSeries"}],"results_per_page":15,"since_id":0,"since_id_str":"0"}'
DT_FORMAT = '%a, %d %b %Y %H:%M:%S +0000'


def store_tweet():
	pass

def scrape_tweets(page=1):
	'''Scrapes one page of tweets and adds to db'''
	fetched = urlfetch.fetch(SCRAPE_URL+str(page))
	json = simplejson.loads(fetched.content)
	results = json['results']
	updated = 0

	if results == []: 
		return 'Empty page'

	for tweet in results:
		text = tweet['text']
		username = tweet['from_user']
		date = datetime.strptime(tweet['created_at'], DT_FORMAT)	

		q = Tweets.all()
		q.filter('text =', text)

		if q.get():
			continue
		else:
			updated += 1
			twt = Tweets(text=text, username=username, date=date)		
			twt.put()

	logging.info('Updated %i entries'%updated)		

def initial_scrape():
	'''Scrapes all tweets possible and adds to db'''
	page = 1
	while page:
		if scrape_tweets(page=page) == "Empty page":
			break
		page += 1
		time.sleep(10)

app = webapp2.WSGIApplication([('/', MainHandler),
							   ('/initial_scrape', InitScrapeHandler),
							  ],
							  debug=True)
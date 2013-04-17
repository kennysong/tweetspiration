import webapp2
import jinja2
import os
import hashlib
import logging
import re
import time
from random import choice
from datetime import datetime
from django.utils import simplejson

from google.appengine.api import urlfetch
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

## Models ##

class Tweets(db.Model):
	text = db.TextProperty() # raw tweet text
	html = db.StringProperty() # formatted, filtered tweet text
	username = db.StringProperty()
	date = db.DateTimeProperty()
	url = db.StringProperty()
	img_url = db.StringProperty()

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
		tweets = get_tweets()

		self.render('index.html', {'tweets':tweets})



class ScrapeHandler(BaseHandler):
	def get(self):		
		updated = scrape_tweets()
		self.write("Updated %i entries"%updated)


## The Magic ##

SCRAPE_URL = 'http://search.twitter.com/search.json?q=(%22someone%20should%22)%20(make%20OR%20build%20OR%20create%20OR%20develop%20OR%20start%20OR%20design%20OR%20invent)%20(software%20OR%20app%20OR%20application%20OR%20tool%20OR%20website%20OR%20site%20OR%20service%20OR%20product%20OR%20company%20OR%20business)&page='
DT_FORMAT = '%a, %d %b %Y %H:%M:%S +0000'

RE_HTTP = re.compile(r"(http://[^ ]+)")
RE_HTTPS = re.compile(r"(https://[^ ]+)")
RE_USERNAME = re.compile(r"(^|\s)@([A-Za-z0-9_]+)")
RE_SS = re.compile(r'(^|\s)(someone\sshould)(\s|$)', re.IGNORECASE)
RE_APP = re.compile(r'(^|\s)(app)(\s|$)', re.IGNORECASE)
RE_APPLICATION = re.compile(r'(^|\s)(application)(\s|$)', re.IGNORECASE)
RE_SITE = re.compile(r'(^|\s)(site)(\s|$)', re.IGNORECASE)
RE_WEBSITE = re.compile(r'(^|\s)(website)(\s|$)', re.IGNORECASE)
RE_COMPANY = re.compile(r'(^|\s)(company)(\s|$)', re.IGNORECASE)
RE_BUSINESS = re.compile(r'(^|\s)(business)(\s|$)', re.IGNORECASE)
RE_TOOL = re.compile(r'(^|\s)(tool)(\s|$)', re.IGNORECASE)
RE_PRODUCT = re.compile(r'(^|\s)(product)(\s|$)', re.IGNORECASE)
RE_SOFTWARE = re.compile(r'(^|\s)(software)(\s|$)', re.IGNORECASE)
RE_SERVICE = re.compile(r'(^|\s)(service)(\s|$)', re.IGNORECASE)

#BUTTON_TEXT = ['Awesome', 'Brilliant', 'Genius', 'Ingenious', 'Clever', 'Superb', 'Terrific', 'Marvelous', 'Fantastic', 'Inspirational', 'Creative']

def get_tweets(page=1):
	'''Fetches one page of (20) tweets'''
	q = Tweets.all()
	q.order('-date')
	tweets = q.run(limit=20)

	return tweets

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
		img_url = tweet['profile_image_url_https']
		url = 'https://twitter.com/'+username+'/status/'+tweet['id_str']
		html = filter_tweet(text)
		
		date = datetime.strptime(tweet['created_at'], DT_FORMAT)	

		q = Tweets.all()
		q.filter('html =', html)

		if q.get():
			continue
		else:
			updated += 1
			twt = Tweets(text=text, html=html, username=username, date=date, url=url, img_url=img_url)		
			twt.put()

	logging.info('Updated %i entries'%updated)
	return updated

def filter_tweet(text):
	text = text.encode('ascii', 'ignore')
	
	# create links in hmtl
	html = RE_HTTP.sub(r'<a href="\1">\1</a>', text)
	html = RE_HTTPS.sub(r'<a href="\1">\1</a>', html)
	html = RE_USERNAME.sub(r'\1<span style="color:#08C">@</span><a href="//twitter.com/\2">\2</a> ', html)
	
	# create colors
	html = RE_SS.sub(r'\1<strong>\2</strong>\3', html)
	html = RE_APP.sub(r'\1<span class="app">\2</span>\3', html)
	html = RE_APPLICATION.sub(r'\1<span class="app">\2</span>\3', html)
	html = RE_SITE.sub(r'\1<span class="site">\2</span>\3', html)
	html = RE_WEBSITE.sub(r'\1<span class="site">\2</span>\3', html)
	html = RE_COMPANY.sub(r'\1<span class="company">\2</span>\3', html)
	html = RE_BUSINESS.sub(r'\1<span class="company">\2</span>\3', html)
	html = RE_TOOL.sub(r'\1<span class="tool">\2</span>\3', html)
	html = RE_PRODUCT.sub(r'\1<span class="tool">\2</span>\3', html)
	html = RE_SOFTWARE.sub(r'\1<span class="tool">\2</span>\3', html)
	html = RE_SERVICE.sub(r'\1<span class="service">\2</span>\3', html)
	
	return html
	
	
#FFB42C; orange
#0FC8CC; blue
#DD6945; red
#94D45A; green
#D15EDE; purple

def initial_scrape():
	'''Scrapes all tweets possible and adds to db'''
	page = 1
	while page:
		if scrape_tweets(page=page) == "Empty page":
			break
		page += 1
		time.sleep(10)

def rand_button():
	return choice(BUTTON_TEXT)

def delete_all():
    db.delete(Tweets.all(keys_only=True))

jinja_env.globals['rand_button'] = rand_button()
app = webapp2.WSGIApplication([('/', MainHandler),
							   ('/scrape', ScrapeHandler),
							  ],
							  debug=True)

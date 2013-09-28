import webapp2
import jinja2
import os
import hashlib
import logging
import re
import secret
import time

from twython import Twython
from random import choice
from datetime import datetime
from django.utils import simplejson

from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.api import memcache

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

## Models ##

class Tweets(db.Model):
	text = db.TextProperty() # raw tweet text
	html = db.TextProperty() # formatted, filtered tweet text
	username = db.StringProperty()
	date = db.DateTimeProperty()
	url = db.StringProperty()
	img_url = db.StringProperty()
	group = db.StringProperty()
	hsh = db.StringProperty()

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
		# parse page param
		page = 1
		if self.rget('p'): 
			try:
				page = int(self.rget('p'))
				if page < 1:
					page = 1
			except:
				page = 1

		group = 'none'
		if self.rget('filter') in GROUPS:
			group = self.rget('filter')

		tweets = get_tweets(page, group)
		next = rand_next_text()
		max_page = get_max_page()

		self.render('index.html', {'tweets':tweets, 'page':page, 'next':next, 'max_page':max_page, 'group':group})

class AboutHandler(BaseHandler):
	def get(self):
		self.render('about.html')

class ScrapeHandler(BaseHandler):
	def get(self):		
		updated = scrape_tweets()
		self.write("Updated %i entries"%updated)


## The Magic ##

SCRAPE_QUERY = '("someone should") (make OR build OR create OR develop OR start OR design OR invent) (software OR app OR application OR tool OR website OR site OR service OR product OR company OR business)'
DT_FORMAT = '%a %b %d %H:%M:%S +0000 %Y'

RE_HTTP = re.compile(r"(http://[^ ]+)")
RE_HTTPS = re.compile(r"(https://[^ ]+)")
RE_USERNAME = re.compile(r"(^|\s)@([A-Za-z0-9_]+)")
RE_SS = re.compile(r'(^|\s)(someone\sshould)(\s|$|[\,\:\;\"\-\.\!\?\'])', re.IGNORECASE)
RE_APP = re.compile(r'(^|\s)(app)(\s|$|[\,\:\;\"\-\.\!\?\'])', re.IGNORECASE)
RE_APPLICATION = re.compile(r'(^|\s)(application)(\s|$|[\,\:\;\"\-\.\!\?\'])', re.IGNORECASE)
RE_SITE = re.compile(r'(^|\s)(site)(\s|$|[\,\:\;\"\-\.\!\?\'])', re.IGNORECASE)
RE_WEBSITE = re.compile(r'(^|\s)(website)(\s|$|[\,\:\;\"\-\.\!\?\'])', re.IGNORECASE)
RE_COMPANY = re.compile(r'(^|\s)(company)(\s|$|[\,\:\;\"\-\.\!\?\'])', re.IGNORECASE)
RE_BUSINESS = re.compile(r'(^|\s)(business)(\s|$|[\,\:\;\"\-\.\!\?\'])', re.IGNORECASE)
RE_TOOL = re.compile(r'(^|\s)(tool)(\s|$|[\,\:\;\"\-\.\!\?\'])', re.IGNORECASE)
RE_PRODUCT = re.compile(r'(^|\s)(product)(\s|$|[\,\:\;\"\-\.\!\?\'])', re.IGNORECASE)
RE_SOFTWARE = re.compile(r'(^|\s)(software)(\s|$|[\,\:\;\"\-\.\!\?\'])', re.IGNORECASE)
RE_SERVICE = re.compile(r'(^|\s)(service)(\s|$|[\,\:\;\"\-\.\!\?\'])', re.IGNORECASE)


GROUPS = ['app', 'website', 'business', 'service', 'tool']
NEXT_TEXT = ['Awesome', 'Brilliant', 'Genius', 'Ingenious', 'Clever', 'Superb', 'Terrific', 'Marvelous', 'Fantastic', 'Inspirational', 'Creative']

def get_tweets(page=1, group='none'):
	'''Fetches one page of (15) tweets'''
	tweets = memcache.get(group+str(page))
	if not tweets:
		q = Tweets.all()
		q.order('-date')

		if group != 'none':
			q.filter('group =', group)

		tweets = q.fetch(limit=15, offset=(page-1)*15)

		memcache.set(group+str(page), tweets)

	return tweets

def get_max_page():
	count = memcache.get('count')
	if not count:
		q = Tweets.all()
		count = q.count()
		memcache.set('count', count)		
	return (count // 15) + 1 #ghetto ceil function

def scrape_tweets(count=15, max_id=None, initial=False):
	'''Scrapes one page of tweets and adds to db'''

	# twython integration
	twitter = Twython(secret.KEY, secret.SECRET, oauth_version=2)
	ACCESS_TOKEN = twitter.obtain_access_token()

	twitter = Twython(secret.KEY , access_token=ACCESS_TOKEN)

	if not max_id:
		results = twitter.search(q=SCRAPE_QUERY, count=count)['statuses']
	else:
		results = twitter.search(q=SCRAPE_QUERY, max_id=max_id, count=count)['statuses']

	# end twython

	print results

	if len(results) == 0: 
		return 'Empty page'

	max_id_str = 0
	updated = 0

	for tweet in results:
		text = tweet['text']
		username = tweet['user']['screen_name']
		img_url = tweet['user']['profile_image_url_https']
		url = 'https://twitter.com/'+username+'/status/'+tweet['id_str']
		html = filter_tweet(text)
		group = get_group(text)
		hsh = hashlib.sha224(html).hexdigest()
		
		date = datetime.strptime(tweet['created_at'], DT_FORMAT)	

		q = Tweets.all()
		q.filter('hsh =', hsh)

		if q.get():
			if initial:
				logging.info(tweet['id_str'])
				max_id_str = tweet['id_str']
			continue
		else:
			if initial:
				logging.info(tweet['id_str'])
				max_id_str = tweet['id_str']			
			updated += 1
			twt = Tweets(text=text, html=html, username=username, date=date, url=url, img_url=img_url, group=group, hsh=hsh)		
			twt.put()



	memcache.delete('none1')
	memcache.delete('count')

	logging.info('Updated %i entries'%updated)

	if initial:
		return max_id_str

	return updated

def get_group(text):
	if RE_COMPANY.search(text) or RE_BUSINESS.search(text):
		group = 'business'
	elif RE_TOOL.search(text) or RE_PRODUCT.search(text) or RE_SOFTWARE.search(text):
		group = 'tool'
	elif RE_SERVICE.search(text):
		group = 'service'
	elif RE_APP.search(text) or RE_APPLICATION.search(text):
		group = 'app'
	elif RE_SITE.search(text) or RE_WEBSITE.search(text):
		group = 'website'
	else:
		group = 'none'
	return group

def filter_tweet(text):
	text = text.encode('ascii', 'ignore')
	
	# create links in hmtl
	html = RE_HTTP.sub(r'<a href="\1">\1</a>', text)
	html = RE_HTTPS.sub(r'<a href="\1">\1</a>', html)
	html = RE_USERNAME.sub(r'\1<span style="color:#08C">@</span><a href="//twitter.com/\2">\2</a>', html)
	
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

def initial_scrape(max_id=0):
	'''Scrapes all tweets possible and adds to db, run only in console'''
	
	while True:
		if max_id: 
			r = scrape_tweets(max_id=max_id, initial=True, count=100)
			max_id = r
		else:
			r = scrape_tweets(initial=True, count=100)
			max_id = r
			
		if r == "Empty page":
			logging.info('reached bottom')
			break

		logging.info('max: ' + str(max_id))
		time.sleep(10)


def rand_next_text():
	return choice(NEXT_TEXT)

def delete_all():
    db.delete(Tweets.all(keys_only=True))

app = webapp2.WSGIApplication([('/', MainHandler),
							   ('/about/?', AboutHandler),
							   ('/scrape', ScrapeHandler),
							  ],
							  debug=True)
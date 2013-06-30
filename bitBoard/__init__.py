import markupsafe
import time
import re
import unicodedata
import datetime
import os
import os.path
try:
	import resource
	have_resource = True
except ImportError:
	have_resource = False
import sys
import flask
from flask import Flask, request, session, g, redirect, url_for, \
		abort, render_template, flash, Markup
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.bcrypt import Bcrypt
from flask.ext.assets import Environment, Bundle
from flask.ext.seasurf import SeaSurf
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.contrib.cache import SimpleCache

# TODO: put this somewhere else. Really.
from flask.ext.wtf import DateField
class OptionalDateField(DateField):
	def process_formdata(self, valuelist):
		if valuelist:
			bits = ' '.join(valuelist)
			if not bits:
				self.data = None
				return
		super(OptionalDateField, self).process_formdata(valuelist)



basedir = os.path.abspath(os.path.dirname(__file__))

from config import *

# for pypy compat.. which is kinda useless atm honestly
if SQLALCHEMY_DATABASE_URI.startswith('postgresql'):
	try:
		import psycopg2
	except ImportError:
		from psycopg2ct import compat
		compat.register()

DEBUG_TB_INTERCEPT_REDIRECTS = False
CSRF_ENABLED = False # for wtforms
SEASURF_INCLUDE_OR_EXEMPT_VIEWS = 'include' if DEBUG else 'exempt'

app = Flask(__name__)
app.config.from_object(__name__)
app.jinja_env.line_statement_prefix = '%'
app.jinja_env.line_comment_prefix = '##'

db = SQLAlchemy(app, session_options=dict(expire_on_commit=False))
bcrypt = Bcrypt(app)

csrf = SeaSurf(app)

assets = Environment(app)
assets.url = '/static/'

if USE_COMPASS:
	css = Bundle('css_assets/normalize.css', 'css_assets/main.css',
		Bundle('css_assets/slate.scss', filters='compass'),
		filters='css_slimmer', output='slate.css')
else:
	css = Bundle('css_assets/normalize.css', 'css_assets/main.css',
		Bundle('css_assets/slate_precompiled.css'),
		filters='css_slimmer', output='slate.css')
assets.register('css_all', css)

#toolbar = DebugToolbarExtension(app)

permissions_cache = SimpleCache()
usergroup_cache = SimpleCache()

def path_to_avatar(avatar_path):
	return os.path.join(AVATAR_DIR, avatar_path.split('?')[0])

def add_null_entities(items, value=None):
	return [(item, value) for item in items]

# shamelessly stolen from Django
def slugify(value):
	value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
	value = re.sub('[^\w\s-]', '', value).strip().lower()
	return re.sub('[-\s]+', '-', value)


def jsonify_errors(form):
	if not form.errors:
		return {}

	return [[form[name].label.text, errors] for name, errors in form.errors.iteritems()]

GUEST_USER_GROUP_ID = 5
from bitBoard.models import User, Usergroup, Config, Notification

@app.before_request
def before_request():
	if request.path.startswith('/static') or \
		request.path.startswith('/favicon'):
		g.start_time = None
		return

	save_req_info = not request.is_xhr

	g.start_time = time.clock()
	if have_resource:
		g.start_rusage = resource.getrusage(resource.RUSAGE_SELF)

	g.effective_group = None
	g.user = None
	if 'userid' in session:
		g.user = User.query.filter_by(id=session['userid']).first()
		if not g.user:
			session.pop('userid')
		else:
			if save_req_info:
				g.user.last_active_at = datetime.datetime.now()
				g.user.last_active_ip = request.remote_addr
			g.effective_group_id = g.user.group_id
			g.effective_group = Usergroup.get_cached(g.user.group_id)

	if not g.effective_group:
		g.effective_group_id = GUEST_USER_GROUP_ID
		g.effective_group = Usergroup.get_cached(GUEST_USER_GROUP_ID)

	# I don't think I like this bit too much...
	g.show_ip_addresses = g.effective_group.is_admin

@app.after_request
def after_request(response):
	if not hasattr(g, 'start_time') or g.start_time is None:
		return response

	try:
		jlo = session['just_logged_out']
		if jlo == 1:
			del session['just_logged_out']
		else:
			session['just_logged_out'] = jlo - 1
	except KeyError:
		pass

	# http://stackoverflow.com/questions/12273889/calculate-execution-time-for-every-page-in-pythons-flask
	if (response.response and response.content_type.startswith("text/html")):
		if response.status_code == 200 or 'X-Custom-Error-Page' in response.headers:
			diff = int((time.clock() - g.start_time) * 1000)  # to get a time in ms

			data = 'Rendered in %dms'
			data = data % (diff,)
			response.response[0] = \
				response.response[0].replace('__BIT_FOOTER_INFO__', data)
			response.headers['content-length'] = len(response.response[0])

	return response

@app.errorhandler(403)
def handle_forbidden(error):
	if 'just_logged_out' in session:
		return redirect(url_for('index'), code=303)
	else:
		return 'Forbidden.', 403

@app.teardown_request
def teardown_request(exception):
	if not hasattr(g, 'start_time') or g.start_time is None:
		return

	if have_resource:
		new = resource.getrusage(resource.RUSAGE_SELF)
		old = g.start_rusage
		u = new.ru_utime - old.ru_utime
		s = new.ru_stime - old.ru_stime
		print('%s Taken %f seconds; %f user, %f system' % (request, time.clock() - g.start_time, u, s))



@app.template_filter('date')
def format_date(timestamp):
	if timestamp is None:
		return 'None'
	return timestamp.strftime('%d %b %Y')

@app.template_filter('time')
def format_time(timestamp):
	if timestamp is None:
		return 'None'
	return timestamp.strftime('%H:%M %p')

@app.template_filter('date_and_time')
def format_date_and_time(timestamp):
	if timestamp is None:
		return 'None'
	return timestamp.strftime('%d %b %Y, %H:%M %p')

@app.template_filter('relative_date')
def format_relative_date(timestamp):
	if timestamp is None:
		return 'Never'

	today = datetime.date.today()
	ts_date = timestamp.date()

	if today == ts_date:
		return 'Today'
	elif (today - datetime.timedelta(days=1)) == ts_date:
		return 'Yesterday'
	else:
		return format_date(timestamp)

@app.template_filter('relative_date_and_time')
def format_relative_date_and_time(timestamp):
	if timestamp is None:
		return 'Never'

	now = datetime.datetime.now()
	today = now.date()
	ts_date = timestamp.date()

	delta = (now - timestamp)

	if delta.days < 1:
		if delta.seconds < 60:
			plural = '' if delta.seconds == 1 else 's'
			return '%d second%s ago' % (delta.seconds, plural)
		elif delta.seconds < 3660:
			minutes = delta.seconds / 60
			plural = '' if minutes == 1 else 's'
			return '%d minute%s ago (%s)' % (minutes, plural, format_time(timestamp))

	if today == ts_date:
		return 'Today, %s' % format_time(timestamp)
	elif (today - datetime.timedelta(days=1)) == ts_date:
		return 'Yesterday, %s' % format_time(timestamp)
	else:
		return format_date_and_time(timestamp)

@app.template_filter('ugly_date_and_time')
def format_ugly_date_and_time(timestamp):
	if timestamp is None:
		return '0'
	return timestamp.strftime('%Y%m%d%H%M%S')

def parse_ugly_date_and_time(raw_timestamp):
	if raw_timestamp == '0':
		return None
	return datetime.datetime.strptime(raw_timestamp, '%Y%m%d%H%M%S')

@app.template_filter('pluralize')
def pluralize(number, word):
	if number == 1:
		return '%d %s' % (number, word)
	else:
		return '%d %ss' % (number, word)


def _update_dategroup(dg, new_date):
	if dg is None:
		dg = {}
		dg['current'] = new_date
		dg['show_now'] = True
	else:
		current = dg['current']
		same = (current.year == new_date.year and
				current.month == new_date.month and
				current.day == new_date.day)
		dg['show_now'] = not same
		dg['current'] = new_date

	return dg


import bitBoard.views.base
import bitBoard.views.user
import bitBoard.views.board
import bitBoard.views.wiki

from bitBoard.views.user import LoginForm
def _get_global_login_form():
	return LoginForm(prefix='login_')

def _get_online_users():
	when = datetime.datetime.now() - datetime.timedelta(minutes=5)
	return User.query.filter(User.last_active_at > when).all()

def _get_notifications():
	if not g.user:
		return None
	return Notification.query.\
		filter_by(recipient=g.user).\
		order_by(db.desc(Notification.id)).\
		limit(15).\
		all()

def _update_and_get_view_count():
	if hasattr(g, 'view_count'):
		return g.view_count
	# atomic update
	Config.query.update(dict(views=Config.views+1))
	config = Config.query.first()
	if config == None:
		config = Config(views=1)
		db.session.add(config)
	g.view_count = config.views
	db.session.commit()
	return g.view_count

from bitBoard import parser
@app.context_processor
def add_template_functions():
	return dict(
			update_dategroup=_update_dategroup,
			current_time=datetime.datetime.now,
			parse_text=parser.parse_text,
			get_global_login_form=_get_global_login_form,
			get_online_users=_get_online_users,
			get_notifications=_get_notifications,
			update_and_get_view_count=_update_and_get_view_count,
			)


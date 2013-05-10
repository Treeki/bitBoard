from bitBoard import app, jsonify_errors, add_null_entities, \
		THREADS_PER_PAGE, POSTS_PER_PAGE, \
		AVATAR_DIR, AVATAR_EXTENSIONS, AVATAR_IMAGE_SIZE, AVATAR_FILE_SIZE, \
		parse_ugly_date_and_time, path_to_avatar
from bitBoard.models import *
from bitBoard.parser import parse_text
from flask import Flask, request, session, g, redirect, url_for, \
		abort, render_template, flash, jsonify, escape, \
		send_from_directory
from flask.ext.wtf import Form, TextField, PasswordField, HiddenField, \
		EqualTo, Required, TextAreaField, RadioField, FileField
from urlparse import urlparse, urljoin
from sqlalchemy.orm import joinedload, subqueryload, defer
from sqlalchemy.sql.expression import true
import os, os.path
import random


def is_safe_url(target):
	if target == '':
		return False
	if target[0] == '/':
		return True
	ref_url = urlparse(request.host_url)
	test_url = urlparse(urljoin(request.host_url, target))
	return test_url.scheme in ('http', 'https') and \
			ref_url.netloc == test_url.netloc


def get_redirect_target():
	for target in request.args.get('next'), request.referrer:
		if not target:
			continue
		if is_safe_url(target):
			return target


class RedirectForm(Form):
	next = HiddenField()

	def __init__(self, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)
		if not self.next.data:
			self.next.data = get_redirect_target() or ''

	def redirect(self, endpoint='index', url=None, **values):
		if is_safe_url(self.next.data):
			return redirect(self.next.data)
		target = get_redirect_target() or url
		return redirect(target or url_for(endpoint, **values), code=303)


@app.route('/')
def root():
	return redirect(url_for('index'), code=301)
@app.route('/index')
def index():
	return render_template('index.html')

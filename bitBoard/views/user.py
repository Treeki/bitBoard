from bitBoard import app, jsonify_errors, add_null_entities, \
		AVATAR_DIR, AVATAR_EXTENSIONS, AVATAR_IMAGE_SIZE, AVATAR_FILE_SIZE, \
		path_to_avatar, \
		OptionalDateField
from bitBoard.views.base import RedirectForm, get_redirect_target
from bitBoard.models import *
from flask import Flask, request, session, g, redirect, url_for, \
		abort, render_template, flash, jsonify, escape, \
		send_from_directory
from flask.ext.wtf import Form, \
		EqualTo, Required, InputRequired, \
		TextField, PasswordField, HiddenField, \
		TextAreaField, RadioField, FileField, IntegerField, \
		SelectField, DateField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from urlparse import urlparse, urljoin
from sqlalchemy.orm import joinedload, subqueryload, defer
from sqlalchemy.sql.expression import true
import os, os.path
import random


class LoginForm(RedirectForm):
	name = TextField('Username', validators=[Required()])
	password = PasswordField('Password', validators=[Required()])

	def __init__(self, *args, **kwargs):
		RedirectForm.__init__(self, *args, **kwargs)
		self.user = None

	def validate(self):
		rv = Form.validate(self)
		if not rv:
			return False

		user = User.query.filter_by(name=self.name.data).first()
		if not user:
			self.name.errors.append('No account exists with that username. Please make sure you typed it in correctly!')
			return False
		if not user.check_password(self.password.data):
			self.password.errors.append('The password you entered is incorrect. Please make sure you typed it in correctly!')
			return False

		self.user = user
		return True

@app.route('/login', methods=['GET', 'POST'])
def login():
	form = LoginForm(prefix='login_')

	if form.validate_on_submit():
		session['userid'] = form.user.id
		flash(u'You have logged in as %s.' % form.user.name)
		return form.redirect('index')

	return render_template('login.html', form=form)

@app.route('/logout')
def logout():
	if 'userid' in session:
		session.pop('userid', None)
		session['just_logged_out'] = 2
		flash('You have logged out.')
	return redirect(get_redirect_target() or url_for('index'), code=303)


@app.route('/users')
def user_list():
	users = User.query.all()
	return render_template('user_list.html', users=users)

@app.route('/avatar/<filename>')
def get_avatar(filename):
	return send_from_directory(AVATAR_DIR, filename)




class RegistrationForm(RedirectForm):
	name = TextField('Username', validators=[Required()])

	password = PasswordField('Password', validators=[Required()])
	confirm_password = PasswordField('Repeat Password', validators=[
		Required(),
		EqualTo('password', message='The two passwords you entered must match.'),
		])

	def validate(self):
		rv = Form.validate(self)

		if self.name.data:
			user = User.query.filter_by(name=self.name.data).first()
			if user:
				self.name.errors.append('An account already exists with this username. Please choose a different one.')
				return False

		return rv


@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegistrationForm()

	if form.validate_on_submit():
		user = User()
		user.name = form.name.data
		user.set_password(form.password.data)

		user.created_ip = request.remote_addr
		user.group = Usergroup.query.filter_by(name=u'Members').first()

		db.session.add(user)
		db.session.commit()

		session['userid'] = user.id
		flash(u'Thank you for signing up! You are now logged in as %s.' % user.name)
		return form.redirect()

	return render_template('register.html', form=form)


@app.route('/user/<int:id>-<name>')
def profile(id, name):
	user = User.query.get(id)
	if not user:
		abort(404)
	if user.name != name:
		return redirect(user.url, code=301)
	return render_template('profile.html', user=user)



# USER EDITING
def url_for_edit_user(route, **kwargs):
	return url_for(route, id=g.edited_user.id, name=g.edited_user.name, **kwargs)
@app.context_processor
def _inject_url_for_edit_user():
	return dict(url_for_edit_user=url_for_edit_user)

@app.route('/edit_settings')
def edit_settings():
	if g.user is None:
		abort(403)
	else:
		url = url_for('edit_profile', id=g.user.id, name=g.user.name)
		return redirect(url, code=303)

def _prepare_edit_user(id, name):
	if g.user is None:
		abort(403)

	if g.user.id == id:
		g.edited_user = g.user
		return g.user
	else:
		if g.effective_group.is_admin:
			user = User.query.get(id)
			if user:
				g.edited_user = user
				return user
			else:
				abort(404)
		else:
			abort(403)


class ProfileForm(Form):
	title = TextField('User Title')

	gender = SelectField('Gender',
		choices=(
			(0, 'Unspecified'),
			(1, 'Male'),
			(2, 'Female')),
		validators=[InputRequired()], coerce=int)

	birthday = OptionalDateField('Birthday')
	birthday_mode = SelectField('Birthday Mode',
		choices=(
			(0, 'Don\'t use'),
			(1, 'Show in Today\'s Birthdays')),
		validators=[InputRequired()], coerce=int)

	location = TextField('Location')
	website = TextField('Website URL')

class AdminProfileForm(ProfileForm):
	name = TextField('Username', validators=[Required()])
	thread_count = IntegerField('Thread Count', validators=[Required()])
	post_count = IntegerField('Post Count', validators=[Required()])
	group = QuerySelectField('Group', get_label='name', validators=[Required()])

@app.route('/user/<int:id>-<name>/edit_profile', methods=['GET', 'POST'])
def edit_profile(id, name):
	user = _prepare_edit_user(id, name)

	is_admin = g.effective_group.is_admin

	form_cls = AdminProfileForm if is_admin else ProfileForm
	form = form_cls(obj=user)

	if is_admin:
		form.group.query = Usergroup.query.order_by(Usergroup.name)

	if form.validate_on_submit():
		form.populate_obj(user)
		db.session.commit()
		flash('Your profile has been saved.')

	return render_template('edit_profile.html',
		is_admin=is_admin, user=user,
		form=form, url=url_for_edit_user('edit_profile'))



class AccountForm(Form):
	current_password = PasswordField('Current Password', validators=[Required()])

	password = PasswordField('Password', validators=[Required()])
	confirm_password = PasswordField('Repeat Password', validators=[
		Required(),
		EqualTo('password', message='The two passwords you entered must match.'),
		])

	def validate(self):
		rv = Form.validate(self)

		if self.current_password.data:
			if not g.user.check_password(self.current_password.data):
				self.current_password.errors.append('The password you entered is incorrect. Please try again.')
				return False

		return rv


@app.route('/user/<int:id>-<name>/edit_account', methods=['GET', 'POST'])
def edit_account(id, name):
	user = _prepare_edit_user(id, name)

	form = AccountForm(obj=user)

	if form.validate_on_submit():
		db.session.commit()
		flash('Your account settings have been saved.')

	return render_template('edit_account.html',
		user=user,
		form=form, url=url_for_edit_user('edit_account'))


class EditPostStyleForm(Form):
	post_style = RadioField('Style',
			choices=(
				(1, 'Simple'),
				(2, 'Advanced')),
			validators=[Required()], coerce=int)
	signature = TextAreaField('Signature')
	post_header = TextAreaField('Advanced Header')
	post_footer = TextAreaField('Advanced Footer')
	stylesheet = TextAreaField('Stylesheet')
	style_url = TextField('External CSS URL')


@app.route('/user/<int:id>-<name>/post_style', methods=['GET', 'POST'])
def edit_post_style(id, name):
	user = _prepare_edit_user(id, name)

	form = EditPostStyleForm(obj=user)

	if form.validate_on_submit():
		form.populate_obj(user)
		db.session.commit()
		flash('Your settings have been saved.')

	return render_template('edit_post_style.html', user=user,
			form=form, url=url_for_edit_user('edit_post_style'))



class AvatarForm(Form):
	image = FileField('Avatar Image', validators=[Required()])

@app.route('/user/<int:id>-<name>/edit_avatar', methods=['GET', 'POST'])
def edit_avatar(id, name):
	user = _prepare_edit_user(id, name)

	errors = []

	form = AvatarForm()
	if form.validate_on_submit():
		file = request.files[form.image.name]

		orig_name = file.filename
		ext = orig_name[orig_name.rindex('.')+1:].lower()

		file.stream.seek(0, os.SEEK_END)
		size = file.stream.tell()

		if ext not in AVATAR_EXTENSIONS:
			errors.append('The uploaded file does not have a valid extension.')
		elif size > AVATAR_FILE_SIZE:
			errors.append('The uploaded file was too big (%.1f kB).' % (size/1024.0))
		else:
			from PIL import Image

			# Looks good so far?
			file.stream.seek(0)
			im = Image.open(file.stream)
			im.verify()

			# reopen it as specified by the PIL docs
			file.stream.seek(0)
			im = Image.open(file.stream)
			w, h = im.size

			if w > AVATAR_IMAGE_SIZE[0] or h > AVATAR_IMAGE_SIZE[1]:
				errors.append('The uploaded file was too large (%d x %d pixels).' % (w,h))
			else:
				file.stream.seek(0)

				filename = '%d.%s' % (user.id, ext)

				if user.avatar_path:
					try:
						os.unlink(path_to_avatar(user.avatar_path))
					except OSError:
						pass
				file.save(os.path.join(AVATAR_DIR, filename))

				rand_token = random.randint(0,1000000)
				user.avatar_path = '%s?%d' % (filename, rand_token)
				db.session.commit()

				flash('Your new avatar has been saved.')


	return render_template('edit_avatar.html',
			form=form, errors=errors, user=user,
			url=url_for_edit_user('edit_avatar'),
			delete_url=url_for_edit_user('delete_avatar'),
			valid_extensions=AVATAR_EXTENSIONS,
			max_kilobytes=AVATAR_FILE_SIZE/1024.0,
			max_width=AVATAR_IMAGE_SIZE[0],
			max_height=AVATAR_IMAGE_SIZE[1])


@app.route('/user/<int:id>_<name>/delete_avatar', methods=['POST'])
def delete_avatar(id, name):
	user = _prepare_edit_user(id, name)

	if user.avatar_path:
		os.unlink(path_to_avatar(user.avatar_path))
		user.avatar_path = None
		db.session.commit()

		flash('Your avatar has been deleted.')

	return redirect(url_for_edit_user('edit_avatar'), code=303)




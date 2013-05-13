from bitBoard import app, jsonify_errors, add_null_entities, \
		THREADS_PER_PAGE, POSTS_PER_PAGE, \
		PM_RECIPIENT_LIMIT, \
		parse_ugly_date_and_time, format_ugly_date_and_time
from bitBoard.views.base import RedirectForm, get_redirect_target
from bitBoard.models import *
from bitBoard.parser import parse_text
from flask import Flask, request, session, g, redirect, url_for, \
		abort, render_template, flash, jsonify, escape
from flask.ext.wtf import Form, TextField, PasswordField, HiddenField, \
		EqualTo, Required, TextAreaField, RadioField, FileField
from sqlalchemy.orm import joinedload, subqueryload, defer
from sqlalchemy.sql.expression import true

def get_viewable_forums():
	# do permission checks here
	return db.session.query(Forum).\
			join(ForumPermissions).\
			filter(ForumPermissions.group_id==g.effective_group_id).\
			filter(ForumPermissions.can_view==True).\
			order_by(Forum.position).\
			options(joinedload('last_thread')).\
			all()
def get_viewable_categories():
	return db.session.query(Category).\
			order_by(Category.position).\
			options(joinedload(Category.forums)).\
			all()

def get_viewable_forum_ids():
	return map(lambda x: x[0],
			db.session.query(ForumPermissions.forum_id).\
			filter_by(group_id=g.effective_group_id, can_view=True).\
			all())

@app.route('/forum')
def forum_index():
	c_query = db.session.query(Category).order_by('position')

	if g.user:
		on_clause = db.and_(
			Thread.id == ThreadRead.thread_id,
			ThreadRead.user_id == g.user.id)

		condition = db.case(
			whens=((ThreadRead.time == None, true()),),
			else_=Thread.last_updated_at > ThreadRead.time)

		subquery = db.session.query(db.func.count(Thread.id)).\
			outerjoin(ThreadRead, on_clause).\
			correlate(Forum).\
			filter(Thread.forum_id == Forum.id, condition).\
			as_scalar()

		entities = (Forum, subquery)
	else:
		entities = (Forum,)

	f_query = db.Query(entities, session=db.session()).\
		order_by(Forum.position).\
		options(joinedload('last_thread'), joinedload('last_thread.last_poster'))

	categories = []
	forum_lists = {}
	for category in c_query:
		list = []
		forum_lists[category.id] = list
		categories.append((category, list))

	if g.user:
		forums = f_query
	else:
		forums = add_null_entities(f_query, 0)

	for forum, unread_count in forums:
		forum_lists[forum.category_id].append((forum, unread_count))

	return render_template('forum_index.html', categories=categories)
	#return redirect(url_for('updated_threads'), code=303)


@app.route('/forum/latest_posts')
def latest_posts():
	viewable = get_viewable_forum_ids()

	posts_and_threads = db.session.query(Post, Thread).\
			filter(Thread.id==Post.thread_id).\
			filter(Thread.forum_id.in_(viewable)).\
			order_by(db.desc(Post.created_at)).\
			options(joinedload('creator')).limit(50).all()
	
	posts = map(lambda x: x[0], posts_and_threads)

	return render_template('post_list.html', mode='latest_posts', posts=posts)


def fetch_threads_and_threadread_query():
	# This bit of code is horrible. Really. Horrible.
	entities = ((Thread, ThreadRead) if g.user else Thread)

	base_query = db.Query(entities, session=db.session()).\
			options(
			joinedload('creator'), joinedload('last_poster'),
			joinedload('last_post')
			).\
			order_by(db.desc(Thread.last_updated_at))

	if g.user:
		read_on_clause = db.and_(
			Thread.id == ThreadRead.thread_id,
			ThreadRead.user_id == g.user.id)
		base_query = base_query.outerjoin(ThreadRead, read_on_clause)

	return base_query

@app.route('/messages')
def private_messages():
	threads = fetch_threads_and_threadread_query().\
			filter(Thread.is_private == True).\
			filter(Thread.private_users.contains(g.user))

	# This is since we depend on the userpanel_base template
	g.edited_user = g.user

	return render_template('thread_list.html',
		mode='private_messages', user=g.user,
		threads=threads)

@app.route('/forum/updated_threads')
def updated_threads():
	viewable = get_viewable_forum_ids()

	threads = fetch_threads_and_threadread_query().\
			filter(Thread.forum_id.in_(viewable)).\
			limit(50)

	if not g.user:
		threads = add_null_entities(threads)

	return render_template('thread_list.html',
		mode='updated_threads',
		threads=threads)

@app.route('/forum/<slug>')
def view_forum(slug):
	forum = Forum.query.filter_by(slug=slug).first()
	if not forum:
		abort(404)
	if not forum.can_be_viewed_by(g.user):
		abort(403)


	base_query = fetch_threads_and_threadread_query().\
		filter(Thread.forum == forum)
	query = base_query.filter(Thread.is_stickied==False)
	pagenum = int(request.args.get('page', 1))

	pagination = query.paginate(pagenum, THREADS_PER_PAGE, error_out=False)

	stickies = base_query.filter(Thread.is_stickied==True).all()

	if not g.user:
		pagination.items = add_null_entities(pagination.items)
		stickies = add_null_entities(stickies)

	return render_template('thread_list.html',
		mode='forum', forum=forum, stickies=stickies,
		threads=pagination.items, pagination=pagination)



def post_page_num(post):
	query = db.session.query(db.func.count(Post.id)).\
		filter(Post.thread_id == post.thread_id, Post.id < post.id)

	count_before = query.scalar()
	page_num = (count_before / POSTS_PER_PAGE) + 1
	return page_num

def redirect_to_post(thread, post):
	if not post:
		return redirect_to_post(thread, thread.last_post)
	page_num = post_page_num(post)
	page_bit = ('?page=%d' % page_num) if page_num != 1 else ''

	url = u'%s%s#post%d' % (post.thread.url, page_bit, post.id)
	return redirect(url, code=303)

@app.route('/forum/<slug>/<int:thread_id>')
@app.route('/forum/<slug>/<int:thread_id>-<thread_slug>')
def view_thread(slug, thread_id, thread_slug=None):
	url_forum = Forum.query.filter_by(slug=slug).first()
	thread = Thread.query.get(thread_id)
	if not thread:
		abort(404)
	if not thread.can_be_viewed_by(g.user):
		abort(403)
	if url_forum != thread.forum or thread_slug != thread.slug:
		return redirect(thread.url, code=301)
	return _base_view_thread(thread)

@app.route('/messages/<int:thread_id>')
@app.route('/messages/<int:thread_id>-<thread_slug>')
def pm_view_thread(thread_id, thread_slug=None):
	thread = Thread.query.get(thread_id)
	if not thread:
		abort(404)
	if not thread.can_be_viewed_by(g.user):
		abort(403)
	if thread_slug != thread.slug:
		return redirect(thread.url, code=301)
	return _base_view_thread(thread)

def _base_view_thread(thread):
	# Find a specific post, if we need to
	if 'findPost' in request.args:
		post_id = int(request.args['findPost'])
		post = Post.query.get(post_id)
		if not post:
			abort(404)
		if post.thread_id != thread.id:
			abort(404)
		return redirect_to_post(thread, post)
	elif 'findPostAfter' in request.args:
		raw_timestamp = request.args['findPostAfter']
		timestamp = parse_ugly_date_and_time(raw_timestamp)

		if timestamp:
			post = Post.query.\
				filter(Post.thread == thread, Post.created_at > timestamp).\
				order_by(db.asc(Post.created_at)).\
				first()
		else:
			post = Post.query.\
				filter(Post.thread == thread).\
				order_by(db.asc(Post.created_at)).\
				first()

		return redirect_to_post(thread, post)
	elif g.user and 'findLastUnread' in request.args:
		read = ThreadRead.query.filter_by(user_id=g.user.id, thread_id=thread.id).first()
		url = u'{0}?findPostAfter={1}'.format( \
			thread.url, format_ugly_date_and_time(read.time))
		return redirect(url, code=303)

	if g.user:
		read = ThreadRead.query.filter_by(user_id=g.user.id, thread_id=thread.id).first()
		if not read:
			read = ThreadRead(user_id=g.user.id, thread_id=thread.id)
			db.session.add(read)
		read.time = datetime.datetime.now()
		db.session.commit()

		notification = Notification.query.\
			filter_by(
				recipient_id=g.user.id, thread_id=thread.id,
				type=Notification.FOLLOWED_THREAD).\
			first()
		if notification:
			db.session.delete(notification)

	query = thread.posts.options(
			joinedload('creator'),
			joinedload('current_version'))

	pagenum = int(request.args.get('page', 1))
	pagination = query.paginate(pagenum, POSTS_PER_PAGE, error_out=False)

	quick_reply = PostForm(formdata=None)
	return render_template('view_thread.html',
			forum=thread.forum, thread=thread,
			posts=pagination.items, pagination=pagination,
			qr_form=quick_reply)



class PostForm(Form):
	content = TextAreaField('Post Content', validators=[Required()])

class ThreadForm(PostForm):
	title = TextField('Title', validators=[Required()])
	subtitle = TextField('Subtitle')

class PrivateThreadForm(ThreadForm):
	recipients = TextAreaField('Recipients')

@app.route('/forum/<forum_slug>/post',
	endpoint='post_thread', methods=['GET', 'POST'])
@app.route('/messages/post', defaults={'is_private': True},
	endpoint='pm_post_thread', methods=['GET', 'POST'])
def post_thread(forum_slug=None, is_private=False):
	if is_private:
		# TODO: g.effective_group.can_send_messages?
		if not g.user:
			abort(403)
		forum = None
		url = url_for('pm_post_thread')
		form = PrivateThreadForm()
	else:
		forum = Forum.query.filter_by(slug=forum_slug).first()
		if not forum:
			abort(404)
		if not forum.can_be_posted_in_by(g.user):
			abort(403)
		url = forum.post_url
		form = ThreadForm()

	recipients = None
	recipient_errors = []
	# This is a bit of an ugly mess, but my brain isn't working right atm and
	# I can't think of a better method. TODO: refactor me?
	if is_private:
		recipients = [g.user]
		r_names = form.recipients.data.split('\n')

		for name in r_names:
			name = name.strip()
			if not name: continue
			u = User.query.filter_by(name=name).first()
			if u:
				if u in recipients: continue
				if u == g.user: continue
				recipients.append(u)
			else:
				recipient_errors.append(u"There doesn't seem to be a user named '%s'." % name)
				actually_valid = False

		if len(recipients) > PM_RECIPIENT_LIMIT:
			recipient_errors.append(u"You have added too many users to this private thread. The current limit is %d users, other than yourself." % (PM_RECIPIENT_LIMIT - 1))
			actually_valid = False
		elif len(recipients) <= 1:
			recipient_errors.append(u"You must enter at least one person other than yourself who will be part of this thread.")
			actually_valid = False


	if form.validate_on_submit() and not recipient_errors:
		thread = Thread(
				title=form.title.data,
				subtitle=form.subtitle.data,
				forum=forum,
				creator=g.user,
				is_private=is_private,
				post_count=1)
		thread.make_slug()
		db.session.add(thread)

		if is_private:
			thread.private_users = recipients
			post_number = -1
		else:
			post_number = g.user.post_count + 1

		post = Post(
				thread=thread,
				creator=g.user,
				created_at=datetime.datetime.now(),
				created_ip=request.remote_addr,
				version_count=1,
				number=post_number)
		db.session.add(post)

		if not is_private:
			g.user.post_count += 1
			g.user.thread_count += 1

			forum.post_count += 1
			forum.thread_count += 1

		thread.update_last_post(post)

		version = PostVersion(
			content=form.content.data,
			post=post,
			creator=g.user,
			created_at=datetime.datetime.now(),
			created_ip=request.remote_addr)
		db.session.add(version)
		post.current_version = version

		db.session.commit()

		flash('Your thread has been posted successfully.')
		return redirect(thread.url, code=303)

	return render_template('post.html',
			is_thread=True,
			is_private=is_private,
			recipient_errors=recipient_errors,
			form=form,
			forum=forum,
			pm_recipient_limit=PM_RECIPIENT_LIMIT,
			url=url)

@app.route('/forum/<forum_slug>/<int:thread_id>-<thread_slug>/reply',
	endpoint='post_reply', methods=['GET', 'POST'])
@app.route('/messages/<int:thread_id>-<thread_slug>/reply',
	endpoint='pm_post_reply', methods=['GET', 'POST'],
	defaults={'is_private': True})
def post_reply(thread_id, thread_slug, forum_slug=None, is_private=False):
	if not is_private:
		url_forum = Forum.query.filter_by(slug=forum_slug).first()

	thread = Thread.query.get(thread_id)
	if not thread:
		abort(404)
	if not thread.can_be_replied_to_by(g.user):
		abort(403)
	if request.method == 'GET':
		url_valid = True
		if not is_private:
			if url_forum != thread.forum:
				url_valid = False
		if thread_slug != thread.slug:
			url_valid = False
		if not url_valid:
			return redirect(thread.reply_url, code=301)

	ajax = ('ajax' in request.values)

	form = PostForm()

	if form.validate_on_submit():
		if is_private:
			post_number = -1
		else:
			post_number = g.user.post_count + 1

		post = Post(
			thread=thread,
			creator=g.user,
			created_at=datetime.datetime.now(),
			created_ip=request.remote_addr,
			version_count=1,
			number=post_number)
		db.session.add(post)

		version = PostVersion(
			content=form.content.data,
			post=post,
			creator=g.user,
			created_at=datetime.datetime.now(),
			created_ip=request.remote_addr)
		db.session.add(version)
		post.current_version = version

		thread.post_count += 1
		if not is_private:
			g.user.post_count += 1
			thread.forum.post_count += 1
		thread.update_last_post(post)

		# This is ugly. Deal with notifications.
		notify_join = db.and_(
			Notification.type == Notification.FOLLOWED_THREAD,
			thread_followers.c.user_id == Notification.recipient_id,
			thread_followers.c.thread_id == Notification.thread_id
			)

		notify_which = db.session.query(thread_followers.c.user_id, Notification.id).\
			filter(thread_followers.c.thread_id == thread.id).\
			filter(thread_followers.c.user_id != g.user.id).\
			outerjoin(Notification, notify_join)
		add_new = []
		update_existing = []

		for uid, nid in notify_which:
			if nid:
				update_existing.append(nid)
			else:
				add_new.append({
					'recipient_id': uid,
					'type': Notification.FOLLOWED_THREAD,
					'thread_id': thread.id
					})

		if update_existing:
			Notification.query.\
				filter(Notification.id.in_(update_existing)).\
				update({'count': Notification.count + 1}, synchronize_session=False)

		if add_new:
			db.session.execute(Notification.__table__.insert(), add_new)


		db.session.commit()

		if not ajax:
			flash('Your reply has been posted.')
			return redirect(post.url, code=303)
		else:
			return jsonify(
				was_posted=True,
				post_id=post.id,
				post_html=render_template('post_box.html',
					post=post,
					postNumber=thread.post_count)
				)

	if not ajax:
		return render_template('post.html',
				form=form,
				thread=thread,
				forum=thread.forum,
				url=thread.reply_url)
	else:
		return jsonify(was_posted=False, errors=jsonify_errors(form))

@app.route('/forum/<forum_slug>/<int:thread_id>-<thread_slug>/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post(forum_slug, thread_id, thread_slug, post_id):
	url_forum = Forum.query.filter_by(slug=forum_slug).first()
	url_thread = Thread.query.get(thread_id)
	post = Post.query.get(post_id)
	thread = post.thread

	if not post:
		abort(404)
	if not post.can_be_edited_by(g.user):
		abort(403)
	if request.method == 'GET' and (url_forum != thread.forum or thread_slug != thread.slug):
		return redirect(post.edit_url, code=301)

	posts_before = Post.query.\
		filter(Post.thread == thread, Post.id < post.id).\
		count()

	edits_thread = (posts_before == 0)

	ajax = ('ajax' in request.values)

	cur_version = post.current_version
	form_cls = ThreadForm if edits_thread else PostForm
	form = form_cls(obj=post,
		content=cur_version.content,
		title=thread.title,
		subtitle=thread.subtitle)

	if 'getQuickEditAjaxForm' in request.args:
		html = render_template('inline_edit.html',
				post=post,
				form=form,
				url=post.edit_url)
		return jsonify(form_html=html)

	if form.validate_on_submit():
		if cur_version.content != form.content.data:
			version = PostVersion(
				content=form.content.data,
				post=post,
				creator=g.user,
				created_at=datetime.datetime.now(),
				created_ip=request.remote_addr)
			db.session.add(version)

			post.version_count += 1
			post.current_version = version

		if edits_thread:
			thread.title = form.title.data
			thread.subtitle = form.subtitle.data
			thread.slug = slugify(thread.title)

		db.session.commit()

		if not ajax:
			flash('Your post has been updated.')
			return redirect(post.url, code=303)
		else:
			return jsonify(
				was_edited=True,
				post_html=escape(parse_text(version.content))
				)

	if not ajax:
		return render_template('post.html',
				form=form,
				is_thread=edits_thread,
				is_edit=True,
				thread=thread,
				forum=thread.forum,
				url=post.edit_url)
	else:
		return jsonify(was_edited=False, errors=jsonify_errors(form))


@app.route('/forum/<forum_slug>/<int:thread_id>-<thread_slug>/<int:post_id>/delete', methods=['GET', 'POST'])
def delete_post(forum_slug, thread_id, thread_slug, post_id):
	url_forum = Forum.query.filter_by(slug=forum_slug).first()
	url_thread = Thread.query.get(thread_id)
	post = Post.query.get(post_id)

	if not post:
		abort(404)
	if not post.can_be_deleted_by(g.user):
		abort(403)
	if request.method == 'GET' and (url_forum != post.thread.forum or thread_slug != post.thread.slug):
		return redirect(post.delete_url, code=301)

	ajax = ('ajax' in request.values)

	if request.method == 'POST':
		post.is_deleted = True
		db.session.commit()

		if not ajax:
			flash('Your post has been deleted.')
			return redirect(post.url, code=303)
		else:
			return jsonify(
				was_deleted=True,
				post_html=render_template('post_box.html', post=post)
				)
	else:
		return render_template('confirm_post_delete.html',
			post=post,
			thread=post.thread,
			forum=post.thread.forum,
			url=post.delete_url)

@app.route('/forum/<forum_slug>/<int:thread_id>-<thread_slug>/lock',
	endpoint='lock_thread', defaults={'action': 'lock'}, methods=['GET', 'POST'])
@app.route('/forum/<forum_slug>/<int:thread_id>-<thread_slug>/sticky',
	endpoint='sticky_thread', defaults={'action': 'sticky'}, methods=['GET', 'POST'])
@app.route('/forum/<forum_slug>/<int:thread_id>-<thread_slug>/follow',
	endpoint='follow_thread', defaults={'action': 'follow'}, methods=['GET', 'POST'])
def thread_mod_action(forum_slug, thread_id, thread_slug, action):
	# This view is becoming spaghetti.
	url_forum = Forum.query.filter_by(slug=forum_slug).first()
	thread = Thread.query.get(thread_id)

	if not thread:
		abort(404)

	forum = thread.forum
	requires_moderator = True
	if action == 'sticky':
		url = thread.sticky_url
	elif action == 'lock':
		url = thread.lock_url
	elif action == 'follow':
		url = thread.follow_url
		requires_moderator = False

	if requires_moderator:
		if not forum.can_be_moderated_by(g.user):
			abort(403)
	else:
		if not forum.can_be_viewed_by(g.user):
			abort(403)

	if request.method == 'GET' and (url_forum != thread.forum or thread_slug != thread.slug):
		return redirect(url, code=301)

	ajax = ('ajax' in request.values)
	form = RedirectForm()

	if action == 'sticky':
		old_value = thread.is_stickied
		attr = 'is_stickied'

		if old_value:
			cap_verb = 'Unstick'
			done_word = 'unstickied'
			link_title = 'Stick'
			message = 'Are you sure you want to make this thread a normal thread?'
		else:
			cap_verb = 'Stick'
			done_word = 'stickied'
			link_title = 'Unstick'
			message = 'Are you sure you want to make this thread a sticky?'
	elif action == 'lock':
		old_value = thread.is_locked
		attr = 'is_locked'

		if old_value:
			cap_verb = 'Unlock'
			done_word = 'unlocked'
			link_title = 'Lock'
			message = 'Are you sure you want to unlock this thread?'
		else:
			cap_verb = 'Lock'
			done_word = 'locked'
			link_title = 'Unlock'
			message = 'Are you sure you want to lock this thread?'
	elif action == 'follow':
		old_value = thread.is_followed_by(g.user)
		attr = None

		if old_value:
			cap_verb = 'Follow'
			link_title = 'Follow'
			message = 'Are you sure you want to follow this thread?'
		else:
			cap_verb = 'Unfollow'
			link_title = 'Unfollow'
			message = 'Are you sure you want to stop following this thread?'


	if request.method == 'POST':
		if action == 'follow':
			if old_value:
				thread.followers.remove(g.user)
				thread.follower_count -= 1
				msg = 'You are no longer following this thread.'
			else:
				thread.followers.append(g.user)
				thread.follower_count += 1
				msg = 'You are now following this thread. You will receive notifications about new posts.'
		else:
			setattr(thread, attr, not old_value)
			msg = 'The thread has been %s.' % done_word
		db.session.commit()


		if ajax:
			return jsonify(toast=msg, link_title=link_title)
		else:
			flash(msg)
			return form.redirect(url=thread.url)
	else:
		return render_template('confirm.html',
			form=form,
			crumbs_type='thread',
			forum=forum, thread=thread,
			final_crumb=('%s Thread' % cap_verb),
			message=message,
			url=url)


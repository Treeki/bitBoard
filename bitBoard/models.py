from bitBoard import db, bcrypt, slugify, GUEST_USER_GROUP_ID, \
	permissions_cache, usergroup_cache, THREADS_PER_PAGE, POSTS_PER_PAGE
from flask import Markup, url_for
import datetime

class Config(db.Model):
	__tablename__ = 'config'

	id = db.Column(db.Integer, primary_key=True) #SQLA wants this...
	views = db.Column(db.Integer, default=0)



class Usergroup(db.Model):
	__tablename__ = 'usergroups'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.Unicode(100))

	users = db.relationship('User', backref='group')

	is_default = db.Column(db.Boolean, default=False)
	is_admin = db.Column(db.Boolean, default=False)

	can_create_wiki_pages = db.Column(db.Boolean, default=True)
	can_edit_wiki_pages = db.Column(db.Boolean, default=True)

	username_tag = db.Column(db.Unicode(100))

	forum_permissions = db.relationship('ForumPermissions', backref='group')

	@classmethod
	def get_cached(cls, id):
		key = str(id)
		value = usergroup_cache.get(key)
		if value is None:
			value = cls.query.get(id)
			db.session.expunge(value)
			usergroup_cache.set(key, value)
		return value





class User(db.Model):
	__tablename__ = 'users'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.Unicode(50), unique=True)

	group_id = db.Column(db.Integer, db.ForeignKey('usergroups.id'), nullable=False)

	created_at = db.Column(db.DateTime, default=datetime.datetime.now)
	created_ip = db.Column(db.String(16))

	last_active_at = db.Column(db.DateTime)
	last_active_ip = db.Column(db.String(16))

	last_post_at = db.Column(db.DateTime)

	notifications = db.relationship('Notification', backref='recipient', lazy='dynamic')

	thread_count = db.Column(db.Integer, default=0)
	post_count = db.Column(db.Integer, default=0)

	threads = db.relationship('Thread',
			lazy='dynamic',
			primaryjoin='and_(Thread.creator_id==User.id, Thread.type==1)')
	posts = db.relationship('Post', backref='creator', lazy='dynamic')

	title = db.Column(db.Unicode(250))

	has_avatar = db.Column(db.Boolean)
	avatar_path = db.Column(db.String(100))

	post_style = db.deferred(db.Column(db.Integer, default=1), group='post_layout')
	signature = db.deferred(db.Column(db.UnicodeText), group='post_layout')
	post_header = db.deferred(db.Column(db.UnicodeText), group='post_layout')
	post_footer = db.deferred(db.Column(db.UnicodeText), group='post_layout')
	stylesheet = db.deferred(db.Column(db.UnicodeText), group='post_layout')
	style_url = db.deferred(db.Column(db.Unicode(250)), group='post_layout')

	birthday = db.Column(db.Date)
	birthday_mode = db.Column(db.Integer, default=0)

	gender = db.Column(db.Integer, default=0)

	email = db.deferred(db.Column(db.Unicode(250)), group='profile')
	email_public = db.deferred(db.Column(db.Boolean, default=False), group='profile')
	personal_info = db.deferred(db.Column(db.UnicodeText), group='profile')

	location = db.Column(db.Unicode(250))
	website = db.Column(db.Unicode(250))

	password_hash = db.Column(db.String(60))
	def check_password(self, password):
		return bcrypt.check_password_hash(self.password_hash, password)
	def set_password(self, password):
		self.password_hash = bcrypt.generate_password_hash(password)

	@property
	def url(self):
		return u'/user/{0}-{1}'.format(self.id, self.name)
		#return url_for('profile', id=self.id, name=self.name)

	@property
	def cached_group(self):
		return Usergroup.get_cached(self.group_id)

	@property
	def link(self):
		raw_html = '<a href=\'%%s\' class=\'userLink\' style=\'text-decoration:none\'>%s</a>' % self.cached_group.username_tag
		return Markup(raw_html) % (self.url, self.name)


class Notification(db.Model):
	__tablename__ = 'notifications'
	id = db.Column(db.Integer, primary_key=True)

	recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

	created_at = db.Column(db.DateTime, default=datetime.datetime.now)
	updated_at = db.Column(db.DateTime, default=datetime.datetime.now)

	count = db.Column(db.Integer, default=1)

	FOLLOWED_THREAD = 1
	NEW_PRIVATE_THREAD = 2
	type = db.Column(db.Integer, nullable=False)

	thread_id = db.Column(db.Integer, db.ForeignKey('threads.id'))
	thread = db.relationship('Thread', uselist=False,
		primaryjoin='Notification.thread_id==Thread.id')

	def __html__(self):
		if self.type == self.FOLLOWED_THREAD:
			if self.count == 1:
				first = u'New post'
			else:
				first = u'%d new posts' % self.count

			return Markup(u'%s in <a href="%s">%s</a>') % \
				(first, self.thread.last_unread_url, self.thread.title)
		elif self.type == self.NEW_PRIVATE_THREAD:
			return Markup(u'%s has invited you to a private thread: <a href="%s">%s</a>') % \
				(self.thread.creator.link, self.thread.url, self.thread.title)
		else:
			return u'(Unknown notification (%d))' % self.type



class Category(db.Model):
	__tablename__ = 'categories'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.Unicode(250), nullable=False)

	position = db.Column(db.Integer)

	forums = db.relationship('Forum', backref='category',
		primaryjoin='Forum.category_id==Category.id',
		order_by='asc(Forum.position)')


class Forum(db.Model):
	__tablename__ = 'forums'
	id = db.Column(db.Integer, primary_key=True)
	slug = db.Column(db.String(50), unique=True)
	name = db.Column(db.Unicode(250), nullable=False)
	description = db.Column(db.UnicodeText)

	category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)

	position = db.Column(db.Integer)

	post_count = db.Column(db.Integer, default=0)
	thread_count = db.Column(db.Integer, default=0)

	threads = db.relationship('Thread', backref='forum',
			primaryjoin='Thread.forum_id==Forum.id',
			lazy='dynamic',
			order_by='desc(Thread.last_updated_at)')

	last_thread_id = db.Column(db.Integer,
		db.ForeignKey('threads.id', use_alter=True, name='fk_last_thread_id'))

	last_thread = db.relationship('Thread',
			uselist=False, post_update=True,
			primaryjoin='Forum.last_thread_id==Thread.id')

	permissions = db.relationship('ForumPermissions', backref='forum', lazy='dynamic')

	@property
	def url(self):
		return u'/forum/{0}'.format(self.slug)
		#return url_for('view_forum', slug=self.slug)

	@property
	def post_url(self):
		return url_for('post_thread', forum_slug=self.slug)

	def permissions_for(self, user):
		g_id = GUEST_USER_GROUP_ID if user is None else user.group_id
		key = '%d_%d' % (self.id, g_id)
		value = permissions_cache.get(key)
		if value is None:
			value = self.permissions.filter_by(group_id=g_id).first()
			db.session.expunge(value)
			permissions_cache.set(key, value)
		return value

	def can_be_viewed_by(self, user):
		return self.permissions_for(user).can_view

	def can_be_posted_in_by(self, user):
		return self.permissions_for(user).can_post_thread

	def can_be_replied_in_by(self, user):
		return self.permissions_for(user).can_reply

	def can_be_moderated_by(self, user):
		return self.permissions_for(user).can_moderate

	def create_default_permissions(self):
		for group in Usergroup.query.all():
			p = ForumPermissions(forum=self, group=group)
			p.can_view = True
			# kinda hacky atm?
			if group.name != u'Guests':
				p.can_reply = True
				p.can_post_thread = True
				if group.name == u'Administrators' or group.name == u'Moderators':
					p.can_moderate = True
			db.session.add(p)
	
	def update_last_thread(self, consider=None):
		self.last_thread = self.threads.first()
		if not self.last_thread or (consider and consider.last_updated_at > self.last_thread.last_updated_at):
			self.last_thread = consider



class ForumPermissions(db.Model):
	__tablename__ = 'forum_permissions'
	forum_id = db.Column(db.Integer, db.ForeignKey('forums.id'), primary_key=True, nullable=False)
	group_id = db.Column(db.Integer, db.ForeignKey('usergroups.id'), primary_key=True, nullable=False)

	can_view = db.Column(db.Boolean)
	can_reply = db.Column(db.Boolean)
	can_post_thread = db.Column(db.Boolean)
	can_moderate = db.Column(db.Boolean)



pm_thread_users = db.Table('pm_thread_users', db.Model.metadata,
	db.Column('thread_id', db.Integer, db.ForeignKey('threads.id')),
	db.Column('user_id', db.Integer, db.ForeignKey('users.id')))

thread_followers = db.Table('thread_followers', db.Model.metadata,
	db.Column('thread_id', db.Integer, db.ForeignKey('threads.id')),
	db.Column('user_id', db.Integer, db.ForeignKey('users.id')))

class Thread(db.Model):
	__tablename__ = 'threads'
	id = db.Column(db.Integer, primary_key=True)
	slug = db.Column(db.String(250))
	title = db.Column(db.Unicode(250), nullable=False)
	subtitle = db.Column(db.Unicode(250))

	forum_id = db.Column(db.Integer, db.ForeignKey('forums.id'), nullable=True)

	BASIC_THREAD = 1
	PRIVATE = 2
	type = db.Column(db.Integer, nullable=False)

	private_users = db.relationship(User,
		secondary=pm_thread_users,
		backref=db.backref('private_threads', lazy='dynamic'))

	follower_count = db.Column(db.Integer, default=0)
	followers = db.relationship(User,
		secondary=thread_followers,
		backref=db.backref('followed_threads', lazy='dynamic'),
		lazy='dynamic')

	def is_followed_by(self, user):
		# I really don't like this. Surely there's got to be a better way? :x
		r = db.session.query(thread_followers).\
				filter_by(thread_id=self.id, user_id=user.id).\
				first()

		return bool(r)

	creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
	creator = db.relationship('User',
		uselist=False,
		primaryjoin='Thread.creator_id==User.id')

	is_locked = db.Column(db.Boolean, default=False)
	is_stickied = db.Column(db.Boolean, default=False)

	last_post_id = db.Column(db.Integer,
		db.ForeignKey('posts.id', use_alter=True, name='fk_last_post_id'))
	last_post = db.relationship('Post',
			uselist=False, post_update=True,
			primaryjoin='Thread.last_post_id==Post.id')

	last_poster_id = db.Column(db.Integer, db.ForeignKey('users.id'))
	last_poster = db.relationship('User',
			uselist=False,
			primaryjoin='Thread.last_poster_id==User.id')

	last_post_at = db.Column(db.DateTime)
	last_updated_at = db.Column(db.DateTime)

	post_count = db.Column(db.Integer, default=0)

	posts = db.relationship('Post', backref='thread',
			primaryjoin='Post.thread_id==Thread.id',
			lazy='dynamic', order_by='Post.id')

	icon = db.Column(db.Integer, default=None)

	@property
	def is_basic_thread(self):
		return self.type == self.BASIC_THREAD
	@property
	def is_private(self):
		return self.type == self.PRIVATE
	def update_last_post(self, consider=None):
		post = self.posts[-1]
		if consider and consider.created_at > post.created_at:
			post = consider
		self.last_post = post
		self.last_poster = post.creator
		self.last_post_at = post.created_at
		self.last_updated_at = post.created_at
		if self.is_basic_thread:
			self.forum.update_last_thread(self)

	def make_slug(self):
		self.slug = slugify(self.title)

	@property
	def url(self):
		if self.is_private:
			return u'/messages/{0}-{1}'.format(self.id, self.slug)
		else:
			return u'/forum/{0}/{1}-{2}'.format(self.forum.slug, self.id, self.slug)
		#return url_for('view_thread', slug=self.forum.slug, id=self.id, thread_slug=self.slug)

	@property
	def last_unread_url(self):
		return self.url + u'?findLastUnread'

	@property
	def last_post_url(self):
		return u'{0}?findPost={1}'.format(self.url, self.last_post_id)
	
	@property
	def reply_url(self):
		if self.is_private:
			return url_for('pm_post_reply',
				thread_id=self.id, thread_slug=self.slug)
		else:
			return url_for('post_reply',
				forum_slug=self.forum.slug,
				thread_id=self.id, thread_slug=self.slug)

	@property
	def follow_url(self):
		return url_for('follow_thread', forum_slug=self.forum.slug, thread_id=self.id, thread_slug=self.slug)
	@property
	def lock_url(self):
		return url_for('lock_thread',
			forum_slug=self.forum.slug,
			thread_id=self.id, thread_slug=self.slug)
	@property
	def sticky_url(self):
		return url_for('sticky_thread',
			forum_slug=self.forum.slug,
			thread_id=self.id, thread_slug=self.slug)
	@property
	def move_url(self):
		return url_for('move_thread',
			forum_slug=self.forum.slug,
			thread_id=self.id, thread_slug=self.slug)

	@property
	def can_be_followed(self):
		return (not self.is_private)

	def can_be_viewed_by(self, user):
		if self.is_private:
			return user in self.private_users
		else:
			return self.forum.can_be_viewed_by(user)

	def can_be_replied_to_by(self, user):
		if self.is_private:
			return self.can_be_viewed_by(user)

		if self.is_locked:
			if not self.forum.can_be_moderated_by(user):
				return False
		return self.forum.can_be_replied_in_by(user)

	@property
	def page_count(self):
		return (self.post_count + POSTS_PER_PAGE - 1) / POSTS_PER_PAGE



class Post(db.Model):
	__tablename__ = 'posts'
	id = db.Column(db.Integer, primary_key=True)

	thread_id = db.Column(db.Integer, db.ForeignKey('threads.id'), nullable=False)
	creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

	number = db.Column(db.Integer)
	version_count = db.Column(db.Integer)

	versions = db.relationship('PostVersion', backref='post',
		primaryjoin='PostVersion.post_id==Post.id',
		order_by='asc(PostVersion.id)')

	current_version_id = db.Column(db.Integer,
		db.ForeignKey('post_versions.id', use_alter=True, name='fk_current_version_id'))
	current_version = db.relationship('PostVersion',
			uselist=False, post_update=True,
			primaryjoin='Post.current_version_id==PostVersion.id')

	created_at = db.Column(db.DateTime, default=datetime.datetime.now)
	created_ip = db.Column(db.String(16))

	is_deleted = db.Column(db.Boolean)

	@property
	def edit_url(self):
		# Posts in private threads cannot currently be edited
		thread = self.thread
		return url_for('edit_post',
				forum_slug=thread.forum.slug,
				thread_id=thread.id, thread_slug=thread.slug,
				post_id=self.id)

	@property
	def delete_url(self):
		# Posts in private threads cannot currently be deleted
		thread = self.thread
		return url_for('delete_post',
				forum_slug=thread.forum.slug,
				thread_id=thread.id, thread_slug=thread.slug,
				post_id=self.id)

	@property
	def url(self):
		thread = self.thread
		if thread.is_private:
			return u'/messages/{0}-{1}?findPost={2}'.format(thread.id, thread.slug, self.id)
		else:
			return u'/forum/{0}/{1}-{2}?findPost={3}'.format(thread.forum.slug, thread.id, thread.slug, self.id)

	def can_be_edited_by(self, user):
		if self.thread.is_private: return False
		return (user == self.creator) or \
			(self.thread.forum and self.thread.forum.can_be_moderated_by(user))

	def can_be_deleted_by(self, user):
		return self.can_be_edited_by(user)


class PostVersion(db.Model):
	__tablename__ = 'post_versions'
	id = db.Column(db.Integer, primary_key=True)

	post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
	creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
	creator = db.relationship('User',
			uselist=False,
			primaryjoin='PostVersion.creator_id==User.id')

	created_at = db.Column(db.DateTime, default=datetime.datetime.now)
	created_ip = db.Column(db.String(16))

	enable_layout = db.Column(db.Boolean, default=True)
	enable_smilies = db.Column(db.Boolean, default=True)
	enable_bbcode = db.Column(db.Boolean, default=True)
	enable_html = db.Column(db.Boolean, default=True)

	content = db.Column(db.UnicodeText, nullable=False)


class ThreadRead(db.Model):
	__tablename__ = 'thread_read'

	thread_id = db.Column(db.Integer, db.ForeignKey('threads.id'), primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
	time = db.Column(db.DateTime, nullable=False)


class WikiPage(db.Model):
	__tablename__ = 'wiki_pages'
	id = db.Column(db.Integer, primary_key=True)

	name = db.Column(db.Unicode(200), nullable=False, unique=True)

	revisions = db.relationship('WikiRevision', backref='page',
		primaryjoin='WikiRevision.page_id==WikiPage.id',
		order_by='asc(WikiRevision.id)')

	current_revision_id = db.Column(db.Integer,
		db.ForeignKey('wiki_revisions.id', use_alter=True, name='fk_current_revision_id'))
	current_revision = db.relationship('WikiRevision',
			uselist=False, post_update=True,
			primaryjoin='WikiPage.current_revision_id==WikiRevision.id')

	@property
	def url(self):
		return url_for('wiki_page', name=self.name)

	@property
	def edit_url(self):
		return url_for('wiki_page_edit', name=self.name)

	@property
	def history_url(self):
		return url_for('wiki_page_history', name=self.name)

	def can_be_edited_by(self, user):
		return (user and user.cached_group.can_edit_wiki_pages)

class WikiRevision(db.Model):
	__tablename__ = 'wiki_revisions'
	id = db.Column(db.Integer, primary_key=True)

	page_id = db.Column(db.Integer, db.ForeignKey('wiki_pages.id'), nullable=False)

	creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
	creator = db.relationship('User',
			uselist=False,
			primaryjoin='WikiRevision.creator_id==User.id')

	created_at = db.Column(db.DateTime, default=datetime.datetime.now)
	created_ip = db.Column(db.String(16))

	content = db.deferred(db.Column(db.UnicodeText, nullable=False))

	char_delta = db.Column(db.Integer)

	description = db.Column(db.UnicodeText)

	@property
	def url(self):
		return url_for('wiki_page_revision',
			name=self.page.name, revision_id=self.id)

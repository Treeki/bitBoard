import bitBoard
from bitBoard.models import *
import os.path

db.create_all()

from alembic.config import Config
from alembic import command
basedir = os.path.abspath(os.path.dirname(__file__))
alembic_cfg = Config(os.path.join(basedir, 'alembic.ini'))
command.stamp(alembic_cfg, "head")

banned = Usergroup(name=u'Banned',
		username_tag=u'<s><span style=\'color: #999999\'>%s</span></s>',
		can_create_wiki_pages=False, can_edit_wiki_pages=False)
db.session.add(banned)

members = Usergroup(name=u'Members',
		username_tag=u'%s')
db.session.add(members)

moderators = Usergroup(name=u'Moderators',
		username_tag=u'<span style=\'color: #17a56f\'><b>%s</b></span>')
db.session.add(moderators)

admins = Usergroup(name=u'Administrators',
		username_tag=u'<span style=\'color: #008912\'><b>%s</b></span>',
		is_admin=True)
db.session.add(admins)

guests = Usergroup(name=u'Guests',
	can_create_wiki_pages=False, can_edit_wiki_pages=False)
db.session.add(guests)

db.session.commit() # so permissions will be set up correctly

u = User(name=u'Admin', group=admins)
u.set_password(u'optimal')
db.session.add(u)
u = User(name=u'TestGuy', group=members)
u.set_password(u'optimal')
db.session.add(u)

category = Category(name=u'Test Category', position=1)
db.session.add(category)

news = Forum(name=u'News Board', slug='news', position=1, category=category,
    description=u'Stuff that goes on the portal. When it\'s eventually made.')
test = Forum(name=u'Test Board', slug='test', position=2, category=category,
    description=u'Anything can go here.')

db.session.add(news)
db.session.add(test)

news.create_default_permissions()
test.create_default_permissions()

#thread = Thread(title=u'Test Thread', subtitle=u'yay', forum=test, creator=u)
#thread.make_slug()
#
#db.session.add(thread)
#
#post = Post(thread=thread, creator=u, content=u'Yay')
#db.session.add(post)



db.session.commit()


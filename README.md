## bitBoard

Well, here goes.. I'm finally committing my shame to a public git repository for
all the world to view.

This is my first non-trivial attempt at writing a web app in something that
isn't PHP. (I don't count my failed attempts using Django, Rails and Pyramid..
seeing as I never got anywhere with those :p) I'm not all too happy with the
state of the code and if you're a better programmer than me you'll probably
think it sucks, but I'm learning as I go along. Okay, enough self-depreciation
for now.

bitBoard is a forum/message board system partly inspired by the (fairly niche)
AcmlmBoard software, but with a more modern look and feel, and with some extra
features. I'm concentrating on the forum as the core, but I've also got a
simple wiki module, and I plan to add a file database which will eventually
power the downloads section on RVLution.net.

### Current features:

- Database agnostic (in theory.. I only test it on PostgreSQL right now)
- User accounts system that allows users to be placed into a Group for different
  privileges
- JavaScript/AJAX progressive enhancement: the user experience is nicer if you
  have JS enabled, but you can still use every feature without it
- Forum:
    - Individual forums sorted into categories
    - Fine-grained permissions system that allows different permissions per
      group and forum
    - Quick reply and inline post editing
    - Threads can be stickied and locked
    - Old versions of posts are stored, for moderators' referencee
    - Basic BBCode (soon to be Markdown?) and fully sanitised HTML in posts
    - Customisable post layouts/styles a la AcmlmBoard
- Wiki:
    - Create and edit pages, view their history
    - Yes, it's really barebones at the moment. It'll get better!
- Nice URLs everywhere
- Security features:
    - All POST requests are protected against CSRF using Flask_SeaSurf, and
      GET requests are not used for anything which can have an effect on the
      site
    - Passwords are securely encoded using BCrypt
    - SQL injection is entirely impossible

I've still got lots left to do. See todo.md in the repo root if you want to see
the ridiculously long list of things I have planned...


### Dependencies I'm currently using:
- alembic 0.5.0 (*which I still need to learn properly... :x*)
- Flask 0.9
- Flask_Assets 0.8
- Flask_Bcrypt 0.5.2
- Flask_DebugToolbar 0.7.1
- Flask_SeaSurf 0.1.16
- Flask_SQLAlchemy 0.16
- Flask_WTF 0.8
- html5lib 0.95
- Jinja2 2.6
- SQLAlchemy 0.8.0
- webassets 0.8
- WTForms 1.0.2

Also, PIL is necessary for validating the dimensions of uploaded avatars.

If you want to modify the CSS, you'll need to install some version of
Sass/Compass to compile it, and change HAVE_COMPASS to True in *__init__.py*.
(I really should separate the config into a different file already.)

If you're not doing that, the pre-compiled version included in the repo should
be fine.

I hope I didn't forget anything.

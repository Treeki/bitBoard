import html5lib
from flask import Markup
from html5lib import sanitizer, treebuilders, treewalkers, serializer
import time
import re

RAW_BBCODE_REGEXES = (
		(r'\[b\](.+?)\[\/b\]', r'<b>\1</b>'),
		(r'\[i\](.+?)\[\/i\]', r'<i>\1</i>'),
		(r'\[u\](.+?)\[\/u\]', r'<u>\1</u>'),
		(r'\[s\](.+?)\[\/s\]', r'<s>\1</s>'),
		(r'\[sup\](.+?)\[\/sup\]', r'<sup>\1</sup>'),
		(r'\[sub\](.+?)\[\/sub\]', r'<sub>\1</sub>'),
		(r'\[size=((&quot;)?)(.+?)(\1)\](.+?)\[\/size\]', r'<font size="\3">\5</font>'),
		(r'\[font=((&quot;)?)(.+?)(\1)\](.+?)\[\/font\]', r'<font face="\3">\5</font>'),
		(r'\[color=((&quot;)?)(.+?)(\1)\](.+?)\[\/color\]', r'<span style="color: \3">\5</span>'),
		(r'\[url](.+?)\[\/url\]', r'<a href="\1">\1</a>'),
		(r'\[url=((&quot;)?)(.+?)(\1)\](.+?)\[\/url\]', r'<a href="\3">\5</a>'),
		(r'\[img](.+?)\[\/img\]', r'<img src="\1" alt="user posted image">'),
		(r'\[spoiler](.+?)\[\/spoiler\]', r'<span class="spoiler">\1</span>'),
		)

BBCODE_REGEXES = [(re.compile(regex), replace) for regex,replace in RAW_BBCODE_REGEXES]

RAW_SMILIES = (
	(':)', 'smile.gif'),
	(';)', 'wink.gif'),
	(':D', 'biggrin.gif'),
	(':LOL:', 'lol.gif'),
	('8-)', 'glasses.gif'),
	(':(', 'frown.gif'),
	(':mad:', 'mad.gif'),
	('>_<', 'yuck.gif'),
	(':P', 'tongue.gif'),
	(':S', 'wobbly.gif'),
	('O_O', 'eek.gif'),
	('o_O', 'bigeyes.gif'),
	('O_o', 'bigeyes2.gif'),
	('^_^', 'cute.gif'),
	('^^;;;', 'cute2.gif'),
	('~:o', 'baby.gif'),
	('x_x', 'sick.gif'),
	(':eyeshift:', 'eyeshift.gif'),
	(':vamp:', 'vamp.gif'),
	('o_o', 'blank.gif'),
	(';_;', 'cry.gif'),
	('@_@', 'dizzy.gif'),
	('-_-', 'annoyed.gif'),
	('>_>', 'shiftright.gif'),
	('<_<', 'shiftleft.gif'),
	(':eyeshift2:', 'eyeshift2.gif'),
	(':glare:', 'glare.png'),
	(':ohdear:', 'ohdear.png'),
	(':approve:', 'approved.gif'),
	(':deny:', 'denied.gif'),
	)

# TODO: don't hardcode a path here
SMILIES_WITH_URLS = [(code, '/static/smilies/%s' % img) for code,img in RAW_SMILIES]
SMILEY_REPLACEMENTS = [(code, "<img src='%s' class='smiley'>" % url) for code,url in SMILIES_WITH_URLS]

class MySanitiser(sanitizer.HTMLSanitizer):
	def sanitize_css(self, style):
		return style

def parse_text(text):
	t1 = time.clock()
	parser = html5lib.HTMLParser(
			tree=treebuilders.getTreeBuilder('etree'),
			tokenizer=MySanitiser)
	t2 = time.clock()

	text = text.replace('\r', '')
	text = text.replace('\n', '<br>')
	t3 = time.clock()

	for search,replace in SMILEY_REPLACEMENTS:
		text = text.replace(search, replace)

	for regex,replace in BBCODE_REGEXES:
		text = regex.sub(replace, text)

	t4 = time.clock()
	doc = parser.parse(text)
	t5 = time.clock()

	walker = treewalkers.getTreeWalker('etree')
	stream = walker(doc)
	s = serializer.htmlserializer.HTMLSerializer()
	output_generator = s.serialize(stream)
	t6 = time.clock()

	done = Markup(''.join(list(output_generator)))
	t7 = time.clock()
	print('Init:%f, BR:%f, Regex:%f, Parse:%f, Serial:%f, Join:%f, All:%f' % (t2-t1, t3-t2, t4-t3, t5-t4, t6-t5, t7-t6, t7-t1))
	return done


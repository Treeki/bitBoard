import html5lib
from flask import Markup
from html5lib import tokenizer, treebuilders, treewalkers, serializer
import time
import re
from xml.sax.saxutils import escape, unescape

RAW_BBCODE_REGEXES = (
		(r'\[b\](.+?)\[\/b\]', r'<b>\1</b>'),
		(r'\[i\](.+?)\[\/i\]', r'<i>\1</i>'),
		(r'\[u\](.+?)\[\/u\]', r'<u>\1</u>'),
		(r'\[s\](.+?)\[\/s\]', r'<s>\1</s>'),
		(r'\[sup\](.+?)\[\/sup\]', r'<sup>\1</sup>'),
		(r'\[sub\](.+?)\[\/sub\]', r'<sub>\1</sub>'),
		(r'\[size=((&quot;)?)(.+?)(\1)\](.+?)\[\/size\]', r'<span style="font-size: \3">\5</span>'),
		(r'\[font=((&quot;)?)(.+?)(\1)\](.+?)\[\/font\]', r'<span style="font-family: \3">\5</span>'),
		(r'\[color=((&quot;)?)(.+?)(\1)\](.+?)\[\/color\]', r'<span style="color: \3">\5</span>'),
		(r'\[url](.+?)\[\/url\]', r'<a href="\1">\1</a>'),
		(r'\[url=((&quot;)?)(.+?)(\1)\](.+?)\[\/url\]', r'<a href="\3">\5</a>'),
		(r'\[img](.+?)\[\/img\]', r'<img src="\1" alt="user posted image">'),
		(r'\[spoiler](.+?)\[\/spoiler\]', r'<span class="spoiler">\1</span>'),
		(r'\[youtube](.+?)\[\/youtube\]', r'<img youtube="\1">'),
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

VALID_TAGS = frozenset([
	'a', 'b', 'i', 'u', 's', 'sup', 'sub', 'big', 'small', 'font',
	'strong', 'em',
	'p', 'br', 'hr',
	'img',
	'blockquote',
	'ul', 'ol', 'li',
	'dl', 'dt', 'dd',
	'span', 'div',
	'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
	])

VALID_ATTRIBUTES = frozenset([
	'class', 'style',
	'href', 'src', 'title', 'alt',
	'colspan', 'rowspan',

	# stuff deprecated by CSS --
	'width', 'height',
	'face', 'size',
	'cellpadding', 'cellspacing', 'align', 'valign', # outdated tables
	])

class MySanitiser(tokenizer.HTMLTokenizer):
	def __iter__(self):
		Characters = 1
		SpaceCharacters = 2
		StartTag = 3
		EndTag = 4
		EmptyTag = 5
		Comment = 6

		for token in super(MySanitiser, self).__iter__():
			token_type = token['type']

			if token_type == Comment:
				pass
			elif token_type == StartTag or token_type == EndTag or token_type == EmptyTag:
				token_name = token['name']
				if token_name in VALID_TAGS:
					yield self.clean_token(token)
				else:
					yield self.invalidate_token(token, token_type)
			else:
				yield token

	def clean_token(self, token):
		try:
			data = token['data']
		except KeyError:
			return token

		if not data:
			return token

		# A SPECIAL CASE --
		StartTag = 3
		if token['type'] == StartTag and token['name'] == 'img':
			if len(data) == 1 and data[0][0] == 'youtube':
				yt_id = data[0][1]
				url = u'http://www.youtube.com/embed/%s' % yt_id

				token['name'] = u'iframe'
				token['data'] = [
					('type', 'text/html'),
					('width', '640'),
					('height', '390'),
					('src', url),
					('frameborder', '0'),
					]
				return token

		# Validate attributes
		new_data = []

		for k, v in data:
			if k in VALID_ATTRIBUTES:
				new_data.append((k,v))

		token['data'] = new_data
		return token

	def invalidate_token(self, token, token_type):
		Characters = 1
		StartTag = 3
		EndTag = 4
		EmptyTag = 5

		if token_type == EndTag:
			token['data'] = u'</%s>' % token['name']
		elif token['data']:
			attrs = ''.join([u' %s="%s"' % (k, escape(v)) for k, v in token['data']])
			token['data'] = u'<%s%s>' % (token['name'], attrs)
		else:
			token['data'] = u'<%s>' % token['name']

		if token.get('selfClosing'):
			token['data'] = token['data'][:-1] + u'/>'

		token['type'] = Characters
		del token['name']
		return token

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


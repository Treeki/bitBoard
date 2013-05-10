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

class MySanitiser(sanitizer.HTMLSanitizer):
	def sanitize_css(self, style):
		return style

def parse_text(text):
	t1 = time.clock()
	parser = html5lib.HTMLParser(
			tree=treebuilders.getTreeBuilder('simpletree'),
			tokenizer=MySanitiser)
	t2 = time.clock()

	text = text.replace('\r', '')
	text = text.replace('\n', '<br>')
	t3 = time.clock()
	for regex,replace in BBCODE_REGEXES:
		text = regex.sub(replace, text)
	t4 = time.clock()
	doc = parser.parse(text)
	t5 = time.clock()

	walker = treewalkers.getTreeWalker('simpletree')
	stream = walker(doc)
	s = serializer.htmlserializer.HTMLSerializer()
	output_generator = s.serialize(stream)
	t6 = time.clock()

	done = Markup(''.join(list(output_generator)))
	t7 = time.clock()
	print('Init:%f, BR:%f, Regex:%f, Parse:%f, Serial:%f, Join:%f, All:%f' % (t2-t1, t3-t2, t4-t3, t5-t4, t6-t5, t7-t6, t7-t1))
	return done


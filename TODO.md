## GENERAL

### Important for initial release

* Use POST requests for /logout
* BBCode
	* Automatic URL linkifying
	* URL checking for src/href attribs
	* Spoiler tag
	* Code tag
* Test/fix the style on IE
	* Make it usable on mobile
* Logging

### Can be done later

* Add some way for users to choose themes and Slate variations
* Notifications system
	* Pruning of old notifications if they're not acted upon
	* Periodic automatic updates of notifications
	* (minor) Use dategroups for the notifications panel
* Report system
* Admin interface
* Clean up CSS


## FORUM

### Important for initial release

* Stop users from being able to delete a thread's first post
* *[kinda done]* Thread following
	* However, there's one interesting issue. I need to exclude people who
	  followed a thread but lose permission to view it (the thread is moved,
	  or their usergroup changes, or their usergroup's permissions change).
* Finish post layout implementation
	* Support Quick Edit - could disable it for layouted posts as a quick fix?
	* Support non-external CSS
* Post previewing
* make post deletion work

### Can be done later

* Add stats to index
* Ninja post warning
* Double post warning
* Allow mods to view previous revisions of posts
* Optional shadow thread creation when a thread is moved
* move posts/split thread

### Fancy features that I might not ever get to

* Automatic AJAX updates with new threads/posts
* Post icons
* Thread tags
* User tagging
* "Thanks" feature a la XDA
* Ranks
* Attachments


## WIKI

* detect ninja edits
* revision diffs
* implement Recent Changes page
* add case-insensitive page name lookups, probably?


## DEPOT

* Submissions of any file, have to be approved by mods
* Ability to subscribe to a specific user
* Haven't yet decided whether I'll roll a depot-specific comments system OR use forum threads/posts as the backend for this
* Notifications for submissions

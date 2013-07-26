## GENERAL

* **[done]** Refactor the config, move it into a separate file, ...
* **[done]** Edit profile
* **[done]** Change password
* **[done]** Avatars
* **[done]** Handle logging out on a protected page correctly
* **[done]** Title tags on all pages
* Notifications system
	* **[done]** Base notification system
	* Pruning of old notifications if they're not acted upon
	* **[done]** Replies to followed threads
	* **[done]** Replies to private threads
	* Depot submissions by users
	* Periodic automatic updates of notifications
	* **[done]** (minor) Hide the notification dropdown when empty
	* (minor) Use dategroups for the notifications panel
* Report system
* Admin interface
* **[done]** Private messages
* Logging
* BBCode inc. embedded YT videos, URL parsing, ...
* ... or maybe I should just switch to Markdown? I dunno.
* Use POST requests for /logout
* Test/fix the style on IE
	* Make it usable on mobile
	* Finish the light theme
	* Add some way for users to choose themes and Slate variations
* case-insensitive username lookups for login and PM recipients, probably?

## FORUM

* Add stats to index
* Stop users from being able to delete a thread's first post
* **[done]** Editing title/subtitle of thread
* **[done]** Editing title/subtitle with Quick Edit (or just disable quick edit for the first post?)
* Ninja post warning
* Double post warning
* Something to thank users for posts
* User tagging
* Thread tags
* Post icons
* **[done]** Read post tracking
* **[done]** Handle findPost URL param
* *[kinda done]* Thread following
	* However, there's one interesting issue. I need to exclude people who
	  followed a thread but lose permission to view it (the thread is moved,
	  or their usergroup changes, or their usergroup's permissions change).
* Allow mods to view previous revisions of posts
* Finish post layout implementation
	* Inject style URLs properly when post_box is added to a page via JS
	* Support non-external CSS
* **[done]** Custom titles
* Automatic updates showing new threads/posts
* Fix the styling on the Latest Posts page...
* Post previewing
* Ranks, MAYBE? dunno

### Moderation features:
* **[done]** sticky/unsticky
* **[done]** close/unclose
* better indication for closed threads?
* **[kinda done]** move thread
	* Shadow threads. Maybe?
	* Still needs to take thread following into account...
* move posts/split thread, later
* Eventually.. attachments, maybe?

## WIKI

* **[done]** View, create and edit pages
* **[done]** View page history
* detect ninja edits
* revision diffs
* implement Recent Changes page
* add case-insensitive page name lookups, probably?

## DEPOT

* Submissions of any file, have to be approved by mods
* Ability to subscribe to a specific user
* Haven't yet decided whether I'll roll a depot-specific comments system OR use forum threads/posts as the backend for this

## TO DO EVENTUALLY

* Clean up CSS
* Make new site themes (light styles, for example)
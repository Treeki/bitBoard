from bitBoard import app
from bitBoard.models import *
from flask import Flask, request, session, g, redirect, url_for, \
		abort, render_template, flash, jsonify, escape
from flask.ext.wtf import Form, TextField, PasswordField, HiddenField, \
		EqualTo, Required, TextAreaField, RadioField, FileField

@app.route('/wiki')
def wiki_main():
	return redirect(url_for('wiki_page', name='Index'), code=303)

@app.route('/wiki/<name>')
def wiki_page(name):
	page = WikiPage.query.filter_by(name=name).first()
	if not page:
		html = render_template('wiki_404.html', page_name=name)
		return html, 404, {'X-Custom-Error-Page': True}

	return render_template('wiki_page.html',
		page=page,
		revision=page.current_revision)

@app.route('/wiki/<name>/<int:revision_id>')
def wiki_page_revision(name, revision_id):
	page = WikiPage.query.filter_by(name=name).first()
	if not page:
		abort(404)
	if page.current_revision_id == revision_id:
		return redirect(page.url, code=303)

	revision = WikiRevision.query.get(revision_id)
	if revision.page_id != page.id:
		abort(404)

	return render_template('wiki_page.html',
		is_old_revision=True,
		page=page, revision=revision)


@app.route('/wiki/<name>/history')
def wiki_page_history(name):
	page = WikiPage.query.filter_by(name=name).first()
	if not page:
		abort(404)

	revisions = WikiRevision.query.\
		filter_by(page=page).\
		order_by(db.desc(WikiRevision.id)).\
		all()

	return render_template('wiki_page_history.html',
		page=page,
		revisions=revisions)


class WikiPageEditForm(Form):
	content = TextAreaField('Page Content', validators=[Required()])
	edit_reason = TextField('Edit Reason', validators=[Required()])

@app.route('/wiki/<name>/edit', methods=['GET', 'POST'])
def wiki_page_edit(name):
	page = WikiPage.query.filter_by(name=name).first()
	if page:
		if not page.can_be_edited_by(g.user):
			abort(403)
		current_content = page.current_revision.content
		is_creating = False
	else:
		if not g.effective_group.can_create_wiki_pages:
			abort(403)
		current_content = None
		is_creating = True
	form = WikiPageEditForm(content=current_content)

	if form.validate_on_submit():
		if not page:
			page = WikiPage(name=name)
			db.session.add(page)

		revision = WikiRevision(
			page=page, creator=g.user,
			created_ip=request.remote_addr,
			description=form.edit_reason.data,
			content=form.content.data)

		page.current_revision = revision

		db.session.add(revision)
		db.session.commit()

		if is_creating:
			flash('Page successfully created.')
		else:
			flash('Page successfully updated.')
		return redirect(page.url, code=303)

	return render_template('wiki_edit.html',
		page_name=name,
		page=page,
		form=form,
		url=url_for('wiki_page_edit', name=name))


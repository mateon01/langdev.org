""":mod:`langdev.web.forum` --- Forum pages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import re
import math
from flask import *
from flaskext.wtf import *
from langdev.forum import Post, Comment
from langdev.web import render
import langdev.web.user
import langdev.web.pager


#: Forum web pages module.
#:
#: .. seealso:: Flask --- :ref:`working-with-modules`
forum = Module(__name__)


def get_post(post_id):
    try:
        return g.session.query(Post).filter_by(id=post_id)[0]
    except IndexError:
        abort(404)


@forum.route('/')
def posts():
    posts = g.session.query(Post) \
                     .order_by(Post.sticky.desc(), Post.created_at.desc())
    cnt = posts.count()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    posts = posts.offset(offset).limit(limit)
    pager = langdev.web.pager.Pager(math.ceil(cnt / float(limit)),
                                    1 + offset / limit)
    return render('forum/posts', posts, posts=posts, pager=pager, limit=limit)


@forum.route('/atom.xml')
def atom():
    limit = int(request.args.get('limit', 20))
    posts = g.session.query(Post).order_by(Post.created_at.desc()).limit(limit)
    xml = render_template('forum/atom.xml', posts=posts)
    response = make_response(xml)
    response.content_type = 'application/atom+xml'
    return response


class PostForm(Form):

    title = TextField('Title', validators=[Required()])
    body = TextAreaField('Body', validators=[Required()])
    sticky = BooleanField('Sticky')
    submit = SubmitField('Submit')


class CommentForm(Form):

    parent_id = SelectField('Reply to', coerce=int, validators=[Optional()])
    body = TextAreaField('Comment', validators=[Required()])
    submit = SubmitField('Submit')

    def fill_comments(self, post):
        self.parent_id.choices = [(c.id, c.body) for c in post.comments]


@forum.route('/<int:post_id>')
def post(post_id, comment_form=None):
    post = get_post(post_id)
    if not comment_form:
        comment_form = CommentForm()
        comment_form.fill_comments(post)
    return render('forum/post', post, post=post, comment_form=comment_form)


@forum.route('/write')
def write_form(form=None):
    langdev.web.user.ensure_signin()
    form = form or PostForm()
    return render('forum/write_form', form, form=form)


@forum.route('/', methods=['POST'])
def write():
    langdev.web.user.ensure_signin()
    form = PostForm()
    if form.validate():
        post = Post(author=g.current_user)
        form.populate_obj(post)
        with g.session.begin():
            g.session.add(post)
        return redirect(url_for('post', post_id=post.id), 302)
    return write_form(form=form)


@forum.route('/<int:post_id>/edit')
def edit_form(post_id, form=None):
    post = get_post(post_id)
    langdev.web.user.ensure_signin(post.author)
    form = form or PostForm(request.form, post)
    return render('forum/edit_form', form, form=form, post=post)


@forum.route('/<int:post_id>', methods=['PUT'])
def edit(post_id):
    post_object = get_post(post_id)
    langdev.web.user.ensure_signin(post_object.author)
    form = PostForm()
    if form.validate():
        with g.session.begin():
            form.populate_obj(post_object)
        return post(post_object.id)
    return edit_form(post_id, form)


@forum.route('/<int:post_id>', methods=['DELETE'])
def delete(post_id):
    post = get_post(post_id)
    langdev.web.user.ensure_signin(post.author)
    with g.session.begin():
        g.session.delete(post)
    return redirect(url_for('posts'), 302)


def get_comment(comment_id, post_id=None):
    comments = g.session.query(Comment).filter_by(id=comment_id)
    if post_id:
        comments = comments.filter_by(post_id=post_id)
    try:
        return comments[0]
    except IndexError:
        abort(404)


@forum.route('/<int:post_id>', methods=['POST'])
@forum.route('/<int:post_id>/<int:comment_id>', methods=['POST'])
def write_comment(post_id, comment_id=None):
    if comment_id:
        parent = get_comment(comment_id, post_id)
        post_object = comment_object.post
    else:
        post_object = get_post(post_id)
        parent = None
    langdev.web.user.ensure_signin()
    form = CommentForm()
    form.fill_comments(post_object)
    if form.validate():
        with g.session.begin():
            cmt = Comment(author=g.current_user, parent=parent)
            form.populate_obj(cmt)
            post_object.comments.append(cmt)
        return comment(post_object.id, cmt.id)
    return post(post_id, form)


@forum.route('/<int:post_id>/<int:comment_id>')
def comment(post_id, comment_id):
    comment = get_comment(comment_id, post_id)
    response = render('forum/base', comment, comment=comment)
    if re.match(r'^(application/xhtml\+xml|text/html)\s*($|;)',
                response.content_type):
        return redirect(url_for('post', post_id=post_id) +
                        '#comment-{0}'.format(comment.id))
    return response


@forum.route('/<int:post_id>/<int:comment_id>', methods=['DELETE'])
def delete_comment(post_id, comment_id):
    comment = get_comment(comment_id, post_id)
    langdev.web.user.ensure_signin(comment.author)
    with g.session.begin():
        g.session.delete(comment)
    return redirect(url_for('post', post_id=post_id), 302)


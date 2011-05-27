""":mod:`langdev.web.thirdparty` --- Third-party applications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import re
from flask import *
from flaskext.wtf import *
from langdev.user import User
from langdev.thirdparty import Application
from langdev.web import render
import langdev.web.user


#: Third-party application pages module.
#:
#: .. seealso:: Flask --- :ref:`working-with-modules`
thirdparty = Module(__name__)


class ApplicationForm(Form):

    title = TextField('Application title',
                      validators=[Required(), Length(2, 100)])
    url = html5.URLField('Application website', validators=[Required()])
    description = TextAreaField('Description', validators=[Required()])
    submit = SubmitField('Create application')


@thirdparty.route('/')
def register_form(form=None):
    """Third-party application registration form."""
    langdev.web.user.ensure_signin()
    form = form or ApplicationForm()
    return render('thirdparty/register_form', form, form=form)


@thirdparty.route('/', methods=['POST'])
def register():
    langdev.web.user.ensure_signin()
    form = ApplicationForm()
    if form.validate():
        app = Application(owner=g.current_user)
        form.populate_obj(app)
        with g.session.begin():
            g.session.add(app)
        return redirect(url_for('app', key=app.key), 302)
    return register_form(form=form)


def get_app(key):
    """Gets an application by its :data:`~langdev.thirdparty.Application.key`.

    :param key: :data:`Application.key <langdev.thidparty.Application.key>`
                to find
    :type key: :class:`str`
    :returns: a found application
    :rtype: :class:`langdev.thirdparty.Application`

    """
    try:
        return g.session.query(Application).filter_by(key=key)[0]
    except IndexError:
        abort(404)


@thirdparty.route('/<app_key>')
def app(app_key):
    """Application detail information."""
    app = get_app(app_key)
    langdev.web.user.ensure_signin(app.owner)
    return render('thirdparty/app', app, app=app)


@thirdparty.route('/<app_key>/sso/<user_login>', methods=['GET', 'POST'])
def sso(app_key, user_login):
    """Simple SSO API."""
    app = get_app(app_key)
    user = langdev.web.user.get_user(user_login)
    success = app.hmac(user.password) == request.values['password']
    return render('thirdparty/sso', success, success=success)


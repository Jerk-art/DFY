from app import db
from app.auth import bp
from app.tasks import send_confirmation_email
from app.auth.forms import SignUpForm
from app.auth.forms import SignInForm
from app.auth.forms import ChangePasswordForm
from app.auth.forms import RequestPasswordChangeForm
from app.models import User
from app.models import VerificationError
from flask import abort
from flask import current_app
from flask import render_template
from flask import redirect
from flask import request
from flask import flash
from flask import url_for
from flask_login import login_user
from flask_login import logout_user
from flask_login import current_user


@bp.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    form = SignUpForm()

    if current_user.is_authenticated:
        redirect(url_for('main.index'))
    if request.method == 'GET':
        return render_template('auth/sign_up.html', form=form)
    else:
        if form.validate_on_submit():
            u = User()
            u.username = form.username.data
            u.email = form.email.data
            u.set_password_hash(form.password.data)
            db.session.add(u)
            db.session.commit()
            send_confirmation_email(u, 'Confirm email.', 'emails/confirm_user')
            flash('User successfully created. Please confirm email and then you will be able to sign in.')
            flash(f'Notice that Your confirmation link expires in {current_app.config["EXPIRATION_TIME"]} minutes!')

            # token = u.get_confirmation_token()
            # print(url_for('auth.confirm_user', token=token, _external=True))

            return render_template('auth/info.html')
        else:
            return render_template('auth/sign_up.html', form=form)


@bp.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    form = SignInForm()

    if current_user.is_authenticated:
        redirect(url_for('main.index'))
    if request.method == 'GET':
        return render_template('auth/sign_in.html', form=form)
    else:
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if not user or not user.check_password(form.password.data):
                flash('Username or password is invalid.')
                return render_template('auth/sign_in.html', form=form)
            if not user.confirmed:
                flash('Please confirm email and then you can sign in.')
                return render_template('auth/sign_in.html', form=form)
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('main.index'))
        else:
            return render_template('auth/sign_in.html', form=form)


@bp.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/confirm_user<token>', methods=['GET'])
def confirm_user(token):
    try:
        user = User.get_user_by_confirmation_token(token)
        if user:
            if not user.confirmed:
                user.confirmed = True
                db.session.add(user)
                db.session.commit()
                flash('Your email confirmed, please sign in.')
                return redirect(url_for('auth.sign_in'))
            else:
                flash('Your email already confirmed!')
                return redirect(url_for('auth.sign_in'))
        else:
            abort(404)
    except VerificationError:
        abort(404)


@bp.route('/request_password_change', methods=['GET', 'POST'])
def request_password_change():
    if current_user.is_authenticated:
        if request.method == 'POST':
            abort(404)
        else:
            send_confirmation_email(current_user, 'Change password.', 'emails/confirm_password_change')

            flash('Please check your email to continue process.')
            flash(f'Notice that Your confirmation link expires in {current_app.config["EXPIRATION_TIME"]} minutes!')

            # token = current_user.get_confirmation_token()
            # print(url_for('auth.confirm_user', token=token, _external=True))

            return render_template('auth/info.html')
    else:
        form = RequestPasswordChangeForm()
        if request.method == 'GET':
            flash('Please enter your email.')
            return render_template('auth/request_password_change.html', form=form)
        else:
            if form.validate_on_submit():
                user = User.query.filter_by(email=form.email.data).first()
                send_confirmation_email(user, 'Change password.', 'emails/confirm_password_change')

                flash('Please check your email to continue process.')
                flash(f'Notice that your confirmation link expires in {current_app.config["EXPIRATION_TIME"]} minutes!')

                return render_template('auth/info.html')
            else:
                flash('Please enter your email.')
                return render_template('auth/request_password_change.html', form=form)


@bp.route('/change_password<token>', methods=['GET', 'POST'])
def change_password(token):
    try:
        user = User.get_user_by_confirmation_token(token)
        form = ChangePasswordForm()
        if user:
            if current_user.is_authenticated:
                if user != current_user:
                    abort(404)
            if request.method == 'GET':
                return render_template('auth/change_password.html', form=form)
            else:
                if form.validate_on_submit():
                    user.set_password_hash(form.password.data)
                    db.session.add(user)
                    db.session.commit()
                    flash('Your password successfully changed!')
                    if current_user.is_authenticated:
                        return render_template('auth/info.html')
                    else:
                        return redirect(url_for('auth.sign_in'))
                else:
                    return render_template('auth/change_password.html', form=form)
        else:
            abort(404)
    except VerificationError:
        abort(404)

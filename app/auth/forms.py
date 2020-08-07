from flask_wtf import FlaskForm
from wtforms import SubmitField
from wtforms import StringField
from wtforms import PasswordField
from wtforms import BooleanField
from wtforms.validators import ValidationError
from wtforms.validators import DataRequired
from wtforms.validators import Email
from wtforms.validators import EqualTo
from app.models import User


class SignUpForm(FlaskForm):
    username = StringField('Username:', validators=[DataRequired()])
    email = StringField('Email:', validators=[DataRequired(), Email()])
    password = PasswordField('Password:', validators=[DataRequired()])
    repeat_password = PasswordField('Repeat Password:', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sigh Up')

    def validate_username(self, username):
        if username.data.find('@') != -1:
            raise ValidationError('Username should not contain "@", please use a different username.')
        if len(username.data) < 4:
            raise ValidationError('Username must be at least 4 symbols long.')
        if len(username.data) > 32:
            raise ValidationError('Username must be less than 32 symbols.')
        if User.query.filter_by(username=username.data).all():
            raise ValidationError('Username is already taken, please use a different username.')

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).all():
            raise ValidationError('Email address is already taken, please use a different email.')

    def validate_password(self, password):
        if len(password.data) < 8:
            raise ValidationError('Password must be at least 8 symbols long.')


class SignInForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField()
    submit = SubmitField('Sign In')

    def validate_username(self, username):
        if username.data.find('@') != -1:
            raise ValidationError('Invalid username.')
        if len(username.data) < 4:
            raise ValidationError('Invalid username.')
        if len(username.data) > 32:
            raise ValidationError('Invalid username.')

    def validate_password(self, password):
        if len(password.data) < 8:
            raise ValidationError('Invalid password.')


class RequestPasswordChangeForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Confirm')

    def validate_email(self, email):
        if not User.query.filter_by(email=email.data).first():
            raise ValidationError('Failed to find user with this email.')


class ChangePasswordForm(FlaskForm):
    password = PasswordField('Password:', validators=[DataRequired()])
    repeat_password = PasswordField('Repeat Password:', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Confirm')

    def validate_password(self, password):
        if len(password.data) < 8:
            raise ValidationError('Password must be at least 8 symbols long.')

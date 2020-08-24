from flask_wtf import FlaskForm
from flask import current_app
from wtforms import SubmitField
from wtforms import SelectField
from wtforms import IntegerField
from wtforms.fields.html5 import URLField
from wtforms.validators import DataRequired, url
from wtforms.validators import ValidationError
from app.tasks import get_yt_file_info
from app.tasks import get_sc_file_info
from app.tasks import is_allowed_duration
from app.tasks import get_yt_playlist_info
from app.tasks import BadUrlError


QUALITY_LIST = [(1, 64), (2, 128), (3, 192), (4, 320)]


def get_quality(num):
    return QUALITY_LIST[num - 1][1]


def content_check(form, field):
    if field.data.startswith('https://www.youtube.com/watch?v=') or field.data.startswith('https://youtu.be/'):
        try:
            info = get_yt_file_info(field.data)
        except BadUrlError:
            raise ValidationError(f'Please check the link for correctness.')
        if not is_allowed_duration(info):
            raise ValidationError(f'Video/music file must be shorter '
                                  f'than {current_app.config["ALLOWED_DURATION"]} minutes.')
    elif field.data.startswith('https://soundcloud.com/'):
        try:
            info = get_sc_file_info(field.data)
        except BadUrlError:
            raise ValidationError(f'Please check the link for correctness.')
        if not is_allowed_duration(info):
            raise ValidationError(f'Video/music file must be shorter '
                                  f'than {current_app.config["ALLOWED_DURATION"]} minutes.')
    else:
        raise ValidationError('Please check link for correctness.')


class DownloadForm(FlaskForm):
    link = URLField(validators=[DataRequired(), url(), content_check])
    submit = SubmitField('Download')


class DownloadForm2(FlaskForm):
    link = URLField(validators=[DataRequired(), url(), content_check])
    quality = SelectField('Quality',
                          choices=QUALITY_LIST,
                          default=3,
                          validators=[DataRequired()],
                          coerce=int)
    submit = SubmitField('Download')


class DownloadPlaylistItemsForm(FlaskForm):
    link = URLField('Link to playlist', validators=[DataRequired(message='Please enter URL.'), url()])
    first_item_number = IntegerField('First item -->',
                                     validators=[DataRequired(message='Please enter both items numbers.')])
    last_item_number = IntegerField('<-- Last item',
                                    validators=[DataRequired(message='Please enter both items numbers.')])
    quality = SelectField('Quality',
                          choices=QUALITY_LIST,
                          default=3,
                          validators=[DataRequired()],
                          coerce=int)
    submit = SubmitField('Download')

    def validate_link(self, link):
        if link.data.startswith('https://www.youtube.com/watch?v='):
            pass
        elif link.data.startswith('https://www.youtube.com/playlist?list=') and len(link.data) > 71:
            pass
        else:
            print(len(link.data))
            raise ValidationError('Please check link for correctness.')

    @staticmethod
    def validate_first_item_number(form, first_item_number):
        if first_item_number.data < 1:
            raise ValidationError('Bad first item number.')
        if form.link.data.startswith('https://www.youtube.com/playlist?list='):
            pid = form.link.data[38:]
        else:
            index = form.link.data.find('&index=')
            pid = form.link.data[49:index]
        try:
            if first_item_number.data > get_yt_playlist_info(pid)['pageInfo']['totalResults']:
                raise ValidationError('Bad first item number.')
        except BadUrlError:
            raise ValidationError('Please check passed link for correctness.')

    def validate_last_item_number(self, last_item_number):
        if last_item_number.data < 2:
            raise ValidationError('Bad first item number.')

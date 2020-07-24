from flask_wtf import FlaskForm
from wtforms import SubmitField
from wtforms.fields.html5 import URLField
from wtforms.validators import DataRequired, url
from wtforms.validators import ValidationError
from app import app
from app.tasks import get_yt_video_info
from app.tasks import is_allowed_duration
from app.tasks import BadUrlError


def content_check(form, field):
    if field.data.startswith('https://www.youtube.com/watch?v='):
        try:
            info = get_yt_video_info(field.data)
        except BadUrlError:
            raise ValidationError(f'Please check the link for correctness.')
        if not is_allowed_duration(info):
            raise ValidationError(f'Video/music file must be shorter than {app.config["ALLOWED_DURATION"]} minutes.')


class DownloadForm(FlaskForm):
    link = URLField(validators=[DataRequired(), url(), content_check])
    submit = SubmitField('submit')

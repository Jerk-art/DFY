import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
try:
    load_dotenv(os.path.join(basedir, '.env'))
except FileNotFoundError:
    pass


class Config:
    SERVER_NAME = "127.0.0.1:5000"
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret'
    DOWNLOAD_PATH = None

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')

    SPOTIFY_UID = os.environ.get('SPOTIFY_UID')
    SPOTIFY_SECRET = os.environ.get('SPOTIFY_SECRET')

    ALLOWED_DURATION = 20
    EXPIRATION_TIME = 5
    MAX_PLAYLIST_ITEMS = 20
    PLAYLIST_PART_SIZE = 3
    PLAYLIST_LIVE_TIME = 3
    MAIN_TIMER_DELTA = 1
    UNCONFIRMED_ACC_EXPIRATION_TIME = 180
    ASYNC_TASKS = True
    SYNC_DOWNLOADINGS = False

    ADMINS = ['ne.ne@ne.com']
    SEND_MAILS = True
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    USE_CELERY = True

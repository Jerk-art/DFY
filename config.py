import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
try:
    load_dotenv(os.path.join(basedir, '.env'))
except FileNotFoundError:
    pass


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
    ALLOWED_DURATION = 20
    EXPIRATION_TIME = 5
    ASYNC_TASKS = True
    ADMINS = ['jerkinston@gmail.com']
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

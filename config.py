import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WORKERS_NUM = os.environ.get('WORKERS_NUM') or 4
    YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
    ALLOWED_DURATION = 20

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from celery import Celery
from celery_config import CeleryConfig
from app.scheduler import Scheduler

import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
scheduler = Scheduler(tasks_save_file=f'app{os.path.sep}scheduler{os.path.sep}tasks.pkl',
                      timers_save_file=f'app{os.path.sep}scheduler{os.path.sep}timers.pkl')


if Config.USE_CELERY:
    celery = Celery(__name__)
    celery.config_from_object(CeleryConfig)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if Config.USE_CELERY:
        celery.conf.update(app.config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app import models
    return app

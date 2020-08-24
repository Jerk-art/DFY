from app import db
from app import login_manager
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from time import time
from jwt import encode
from jwt import decode
from pickle import dump
from pickle import load
from os.path import sep


class VerificationError(Exception):
    pass


class Task(db.Model):
    """Object which represent task on the application

    status_codes = {'running': 0, 'completed': 1, 'error': 2, 'running_long_term': 3, 'waiting_on_user': 4}
    """

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(128), index=True)
    user_ip = db.Column(db.String(16), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    status_code = db.Column(db.Integer, index=True)
    progress = db.Column(db.String(128))
    unique_process_info = db.Column(db.String(128))
    files = db.relationship('FileInfo', backref='task', lazy='dynamic')

    def __repr__(self):
        return f'<Task {self.id}>'

    def force_stop(self, progress="Forced stop"):
        """Change task status and progress to force stopped

        :param progress: string to be written into the progress
        :type progress: str
        """

        self.status_code = 1
        self.progress = progress

    @staticmethod
    def stop_all_tasks():
        """Use force_stop to all uncompleted tasks"""

        print("Stopping uncompleted tasks.")
        counter = 0
        for task in Task.query.filter_by(status_code=0).all():
            task.force_stop()
            db.session.add(task)
            db.session.commit()
            counter += 1
        if counter == 1:
            print(f"Stopped 1 task")
        else:
            print(f"Stopped {counter} tasks")


class User(UserMixin, db.Model):
    """User object"""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, index=True)
    email = db.Column(db.String(320), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User "{self.username}">'

    def set_password_hash(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_confirmation_token(self):
        return encode({'value': self.id, 'exp': time() + current_app.config['EXPIRATION_TIME'] * 60},
                      current_app.config['SECRET_KEY'],
                      algorithm='HS256').decode('utf-8')

    @staticmethod
    def get_user_by_confirmation_token(token):
        try:
            id = decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['value']
        except:
            raise VerificationError()
        return User.query.get(id)


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


class FileInfo(db.Model):
    """Playlist object

    status_codes = {'not_processed': 0, 'processed': 1, 'procession_error': 2}
    """

    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Integer)
    file_id = db.Column(db.String(128), index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), index=True)
    status_code = db.Column(db.Integer, nullable=False, default=0)

    @classmethod
    def make_records(cls, list_, task_id):
        i = 0
        for record in list_:
            db.session.add(cls(index=int(i), file_id=record, task_id=task_id))
            i += 1
        db.session.commit()

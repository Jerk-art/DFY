from app import db


class TaskError(Exception):
    pass


class Task(db.Model):
    """Object which represent task on the application"""

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(128), index=True)
    user_ip = db.Column(db.String(16), index=True)
    status_code = db.Column(db.Integer, index=True)
    progress = db.Column(db.Integer)

    status_codes = {'running': 0, 'completed': 1, 'error': 2}

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

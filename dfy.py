from app import create_app, db
from app.models import Task
from app.models import User
from app.models import FileInfo

app = create_app()
app.app_context().push()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Task': Task, 'User': User, 'FileInfo': FileInfo}

from app import create_app, db
from app.models import Task
from sqlalchemy.exc import OperationalError

app = create_app()
app.app_context().push()
try:
    Task.stop_all_tasks()
except OperationalError:
    pass


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Task': Task}

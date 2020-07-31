from app import create_app, db
from app.models import Task

app = create_app()
app.app_context().push()
Task.stop_all_tasks()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Task': Task}

from app import create_app, scheduler
from multiprocessing import Process
from app.scheduler.tasks import tasks
from app.scheduler.tasks import timers

app = create_app()
app.app_context().push()

scheduler.register_tasks(tasks)
scheduler.register_timers(timers)
Process(target=scheduler.run, daemon=True).start()

app.run()

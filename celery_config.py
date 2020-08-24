from kombu import Queue


class CeleryConfig:
    result_backend = 'redis://localhost:6379'
    broker_url = 'redis://localhost:6379'
    task_default_queue = 'default'
    task_queues = (Queue('default', routing_key='task.#'), Queue('downloading_tasks', routing_key='download.#'))
    include = [f'app.tasks']
    task_default_exchange = 'tasks'
    task_default_exchange_type = 'topic'
    task_default_routing_key = 'task.default'

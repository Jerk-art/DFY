from kombu import Queue


class CeleryConfig:
    TASK_DEFAULT_QUEUE = 'default'
    TASKS_QUEUES = (Queue('default', routing_key='task.#'), Queue('downloading_tasks', routing_key='download.#'))
    INCLUDE = [f'app.tasks']
    TASK_DEFAULT_EXCHANGE = 'tasks'
    TASK_DEFAULT_EXCHANGE_TYPE = 'topic'
    TASK_DEFAULT_ROUTING_KEY = 'task.default'

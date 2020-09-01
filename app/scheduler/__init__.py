import datetime
import pickle
import threading
import atexit
import asyncio
import copy
import time


class FileNotDefinedError(Exception):
    pass


class Timer:
    def __init__(self, name, time_delta: datetime.timedelta):
        self.name = name
        self.tasks = list()
        self.time_delta = time_delta

    async def run(self, print_lock: threading.Lock):
        sleep_time = self.time_delta.total_seconds()
        while True:
            await asyncio.sleep(sleep_time)
            for task in self.tasks:
                Timer.run_task(task, print_lock)

    def subscribe_task(self, task):
        self.tasks.append(task)

    @staticmethod
    def run_task(task: dict, print_lock: threading.Lock):
        args = copy.deepcopy(task['args'])
        args.append(print_lock)
        threading.Thread(target=task['func'], args=args, daemon=True).start()


'''task = {'func': None, 'args': list, 'time': str, 'timer_name': str}'''
''' rates: on_start, on_exit, on_timer'''
'''schedule = {'on_start': list, 'on_exit': list}'''


class Scheduler:
    def __init__(self, tasks_save_file=None, timers_save_file=None):
        self.tasks = None
        self.timers = None
        self.schedule = {'on_start': [], 'on_exit': []}
        self.tasks_save_file = tasks_save_file
        self.timers_save_file = timers_save_file

    def register_tasks(self, tasks: list):
        self.tasks = tasks

    def register_timers(self, timers: dict):
        self.timers = timers

    def run(self):
        self.apply_schedule()
        print_lock = threading.Lock()
        for task in self.schedule['on_start']:
            Scheduler.run_task(task, print_lock)
            time.sleep(0.2)
        for task in self.schedule['on_exit']:
            atexit.register(task['func'], *task['args'], print_lock)
        asyncio.get_event_loop().run_until_complete(self.run_timers(print_lock))

    async def run_timers(self, print_lock: threading.Lock):
        if self.timers:
            for key in self.timers:
                future = asyncio.ensure_future(self.timers[key].run(print_lock))
            await future

    def schedule_task(self, task: dict):
        if task['time'] == 'on_start':
            self.schedule['on_start'].append(task)
        elif task['time'] == 'on_exit':
            self.schedule['on_exit'].append(task)
        elif task['time'] == 'on_timer':
            try:
                self.timers[task['timer_name']].subscribe_task(task)
            except KeyError:
                raise Exception(f'Timer named {task["timer_name"]} is not registered')
            except TypeError:
                raise Exception(f'Timer named {task["timer_name"]} is not registered')

    @staticmethod
    def run_task(task: dict, print_lock: threading.Lock):
        args = copy.deepcopy(task['args'])
        args.append(print_lock)
        threading.Thread(target=task['func'], args=args, daemon=True).start()

    def apply_schedule(self):
        for task in self.tasks:
            self.schedule_task(task)

    def save_tasks(self):
        if self.tasks_save_file:
            with open(self.tasks_save_file, 'wb') as file:
                pickle.dump(self.tasks, file)
        else:
            raise FileNotDefinedError

    def save_timers(self):
        if self.timers_save_file:
            with open(self.timers_save_file, 'wb') as file:
                pickle.dump(self.timers, file)
        else:
            raise FileNotDefinedError

    @staticmethod
    def load_tasks_from_file(file):
        with open(file, 'rb') as file:
            tasks = pickle.load(file)
        return tasks

    @staticmethod
    def load_timers_from_file(file):
        with open(file, 'rb') as file:
            timers = pickle.load(file)
        return timers

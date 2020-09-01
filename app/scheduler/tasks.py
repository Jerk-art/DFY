from app import create_app, db
from app.models import Task
from app.models import User
from app.scheduler import Timer
from app.tasks.download import resume_yt_files_downloading
from sqlalchemy.exc import OperationalError
from datetime import datetime
from datetime import timedelta
from flask import current_app

import operator
import pickle
import shutil
import os


def stop_broken_tasks(print_lock):
    app = create_app()
    with app.app_context():
        try:
            Task.stop_tasks(prefix='[Scheduler] ', print_lock=print_lock)
        except OperationalError:
            pass


def delete_unconfirmed_accounts(print_lock):
    app = create_app()
    with app.app_context():
        users = User.query.filter_by(confirmed=False).all()
        with print_lock:
            print('[Scheduler] Checking unconfirmed users')
        time = datetime.now()
        count = 0
        for user in users:
            if (time - user.registration_time).total_seconds() >\
                    current_app.config['UNCONFIRMED_ACC_EXPIRATION_TIME'] * 60:
                db.session.delete(user)
                db.session.commit()
                count += 1
            else:
                pass
        if count == 0:
            pass
        elif count == 1:
            with print_lock:
                print('[Scheduler] Deleted 1 user')
        else:
            with print_lock:
                print(f'[Scheduler] Deleted {count} users')


def clear_junk(print_lock):
    app = create_app()
    with print_lock:
        print('[Scheduler] Checking for junk')
    with app.app_context():
        count = 0
        tasks = Task.query.filter_by(status_code=1, junk_cleared=False).all()
        for task in tasks:
            if task.description == 'Downloading mp3' and (datetime.now() - task.completed_at).total_seconds() < 300:
                continue
            dir = os.path.dirname(os.path.realpath(__file__)).replace(f'scheduler', f'tasks{os.path.sep}temp')
            if task.user_id:
                dir += os.path.sep + str(task.user_id) + os.path.sep + f'Task{task.id}'
            else:
                dir += os.path.sep + str(task.user_ip) + os.path.sep + f'Task{task.id}'
            try:
                shutil.rmtree(dir)
                count += 1
            except FileNotFoundError:
                pass
            task.junk_cleared = True
            db.session.add(task)
            db.session.commit()
        if tasks:
            with print_lock:
                print(f'[Scheduler] Deleted {count} junk directories')


def check_ready_to_download_tasks(print_lock):
    app = create_app()
    with app.app_context():
        with print_lock:
            print('[Scheduler] Checking performed long term tasks')
        counter = 0
        tasks = Task.query.filter_by(status_code=4).all()
        for task in tasks:
            if (datetime.now() - task.completed_at).total_seconds() > app.config['PLAYLIST_LIVE_TIME'] * 60:
                task.progress = 'Done'
                task.status_code = 1
                db.session.add(task)
                db.session.commit()
                counter += 1
                with print_lock:
                    if counter == 1:
                        print('[Scheduler] Closed 1 task')
                    else:
                        print(f'[Scheduler] Closed {counter} tasks')


def resume_long_term_tasks(print_lock):
    app = create_app()
    with print_lock:
        print('[Scheduler] Checking for stopped long term tasks')
    counter = 0
    with app.app_context():
        tasks = Task.query.filter_by(status_code=3).all()
        for task in tasks:
            counter += 1
            sep = os.path.sep
            path_to_task = f'.{sep}app{sep}tasks{sep}temp{sep}{task.user_id}{sep}Task{task.id}'
            with open(path_to_task + sep + 'kwargs', 'rb') as file:
                kwargs = pickle.load(file)
            resume_long_term_task(kwargs, task, path_to_task)

            with print_lock:
                if counter == 1:
                    print('[Scheduler] Resumed 1 long term task')
                else:
                    print(f'[Scheduler] Resumed {counter} long term tasks')


def resume_long_term_task(kwargs, task, path_to_task):
    archives = list()
    playlist = list()
    for file in task.files.all():
        if file.index == 0:
            archives.append(file)
        else:
            playlist.append(file)
    index = 0
    for file in sorted(archives, key=operator.attrgetter('file_id'))[:-1]:
        try:
            if file.check_file_hash(path_to_task + os.path.sep + file.file_id):
                index += 1
            else:
                break
        except FileNotFoundError:
            break
    loaded_files_num = kwargs['part_size'] * index
    playlist = [el.file_id for el in sorted(playlist, key=operator.attrgetter('index'))[loaded_files_num:]]
    resume_yt_files_downloading(playlist, task=task, dir=kwargs['dir'], quality=kwargs['quality'],
                                repair_tags=kwargs['repair_tags'], part_size=kwargs['part_size'],
                                first_part_index=index)


app = create_app()
with app.app_context():
    timer = Timer('main_timer', time_delta=timedelta(minutes=current_app.config['MAIN_TIMER_DELTA']))
timers = {timer.name: timer}

task1 = {'func': stop_broken_tasks, 'args': [], 'time': 'on_start'}
task2 = {'func': delete_unconfirmed_accounts, 'args': [], 'time': 'on_start'}
task3 = {'func': delete_unconfirmed_accounts, 'args': [], 'time': 'on_timer', 'timer_name': 'main_timer'}
task4 = {'func': clear_junk, 'args': [], 'time': 'on_start'}
task5 = {'func': check_ready_to_download_tasks, 'args': [], 'time': 'on_timer', 'timer_name': 'main_timer'}
task6 = {'func': clear_junk, 'args': [], 'time': 'on_exit'}
task7 = {'func': clear_junk, 'args': [], 'time': 'on_timer', 'timer_name': 'main_timer'}
task8 = {'func': resume_long_term_tasks, 'args': [], 'time': 'on_start'}

tasks = [task1, task2, task3, task4, task5, task6, task7, task8]

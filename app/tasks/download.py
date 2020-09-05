from app import create_app
from app import db
from app.models import Task
from app.models import FileInfo
from app.tasks.mail import send_file_ready_email
from app.tasks.mail import send_file_fail_email
from app.tasks.info import get_yt_file_info
from app.tasks.info import is_allowed_duration
from app.tasks.info import BadUrlError
from app.tasks.tags import get_repaired_tags_for_yt
from app.tasks.tags import get_repaired_tags_for_sc
from app.tasks.tags import insert_tags
from flask import send_from_directory
from flask import current_app
from threading import Thread
from sqlalchemy.exc import InvalidRequestError
from config import Config

import pickle
import datetime
import shutil
import youtube_dl
import time
import zipfile
import os


def download(link: str, task=None, dir=None, quality=192, log_info=None, repair_tags=False):
    """Download file and convert to mp3 using youtube-dl API


    :param link: link to youtube or soundcloud file
    :type link: str
    :param dir: path to directory where should be downloaded file,
                if not specified or None, using temp directory in where placed this .py file
    :type dir: str
    :param task: task object or None
    :type task: Task or None
    :param quality: quality to be converted into
    :type quality: int

    :returns: path to downloaded file
    :rtype: str
    """
    print(f'quality is: {quality}')

    if current_app.config['DOWNLOAD_PATH']:
        dir = current_app.config['DOWNLOAD_PATH']
    else:
        dir = dir or os.path.dirname(os.path.realpath(__file__)) + os.path.sep + 'temp'
    if task:
        dir += os.path.sep + f'Task{task.id}'
    filename = str()

    class Logger:
        def debug(self, msg):
            pass

        def info(self, msg):
            pass

        @staticmethod
        def error(msg):
            print(msg)

    def progress_hook(d):
        if d['status'] == 'finished':
            print('Done downloading, now converting...')
            if task and task.description == 'Downloading mp3':
                task.progress = 'Converting'
                db.session.add(task)
                db.session.commit()

            nonlocal filename
            filename = d['filename']
        else:
            try:
                print(f'progress: {d["downloaded_bytes"] / d["total_bytes"] * 100:2.2f}%  speed:{d["speed"] / 1000}')
            except TypeError:
                pass
            except KeyError:
                print(f'progress: {d["_percent_str"]}')

    ydl_opts = {
        'outtmpl': f'{dir}/%(title)s.%(ext)s',
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': str(quality),
        }],
        'logger': Logger(),
        'progress_hooks': [progress_hook],
    }

    if log_info:
        print(log_info)
    else:
        print('Downloading')
    if task and task.description == 'Downloading mp3':
        task.progress = 'Downloading'
        db.session.add(task)
        db.session.commit()
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])
    print('Done converting')
    if repair_tags:
        if link.startswith('https://www.youtube.com/watch?v='):
            tags = get_repaired_tags_for_yt(link[32:43])
        elif link.startswith('https://youtu.be/'):
            tags = get_repaired_tags_for_yt(link[17:])
        else:
            tags = get_repaired_tags_for_sc(link)
        insert_tags(filename[:filename.rfind('.')] + '.mp3', tags)
    return filename


def download_yt_files_sync(playlist: list, task_id=None, dir=None, quality=192, repair_tags=False, app=None,
                           send_mails=True):
    if not app:
        app = create_app()
    app.config['SEND_MAILS'] = send_mails
    app_context = app.app_context()
    app_context.push()

    part_size = current_app.config['PLAYLIST_PART_SIZE']
    if task_id:
        task = Task.query.get(task_id)
    else:
        task = None

    arcpath = (dir + os.path.sep + 'playlist.zip' or 'playlist.zip')

    working_dir = os.getcwd()
    errors_num = 0
    counter = 0
    files_len = len(playlist)
    parts_num = int(files_len / part_size + 1) if files_len % part_size else int(files_len / part_size)

    arc_info = None
    if task:
        try:
            task.progress = f'Preparing for downloading'
            db.session.add(task)
            db.session.commit()
        except InvalidRequestError:
            time.sleep(5)
            task.progress = f'Preparing for downloading'
            db.session.add(task)
            db.session.commit()

        arc_info = FileInfo.query.filter_by(index=0, file_id='playlist.zip', task_id=task.id).first()

    errors_list = []

    for part in range(0, parts_num):
        part_info = None
        if task:
            part_info = FileInfo(index=0, file_id=f'part{part + 1}.zip', task_id=task.id)
            db.session.add(part_info)
            db.session.commit()
        with zipfile.ZipFile(dir + os.path.sep + f'part{part + 1}.zip', 'w') as archive:
            for record in playlist[part * part_size: (part + 1) * part_size]:
                counter += 1
                time.sleep(2)
                if task:
                    file_info = task.files.filter_by(file_id=record).first()
                try:
                    link = 'https://www.youtube.com/watch?v=' + record
                    info = get_yt_file_info(link)
                except BadUrlError:
                    if task:
                        file_info.status_code = 2
                        db.session.add(file_info)
                        db.session.commit()
                    errors_num += 1
                    errors_list.append(link)
                    continue

                if not is_allowed_duration(info):
                    if task:
                        file_info.status_code = 2
                        db.session.add(file_info)
                        db.session.commit()
                    errors_num += 1
                    errors_list.append(link)
                    continue

                if task:
                    task.progress = f'Downloading {counter} of {files_len}'
                    db.session.add(task)
                    db.session.commit()

                try:
                    filename = download(link, task=None, dir=dir, quality=quality, repair_tags=repair_tags,
                                        log_info=f'Downloading {counter} of {files_len}', )
                    dirname = os.path.dirname(filename)
                    os.chdir(dirname)
                    filename = '.'.join((filename.split(os.sep)[-1].split('.')[:-1])) + '.mp3'
                    archive.write(filename)
                    os.remove(filename)
                    os.chdir(working_dir)
                    if task:
                        file_info.status_code = 1
                        db.session.add(file_info)
                        db.session.commit()

                except youtube_dl.DownloadError:
                    if task:
                        file_info.status_code = 2
                        db.session.add(file_info)
                        db.session.commit()

                    errors_num += 1
                    errors_list.append(link)

        if task:
            part_info.set_file_hash(dir + os.path.sep + f'part{part + 1}.zip')
            db.session.add(part_info)
            db.session.commit()

    with zipfile.ZipFile(arcpath, 'w') as archive:
        for part in range(0, parts_num):
            with zipfile.ZipFile(dir + os.path.sep + f'part{part + 1}.zip', 'r') as part_:
                extraction_dir = dir + os.path.sep + 'extract'
                os.mkdir(extraction_dir)
                part_.extractall(path=extraction_dir)
                os.chdir(extraction_dir)
                for el in os.listdir('./'):
                    archive.write(el)
                os.chdir(working_dir)
                shutil.rmtree(extraction_dir)
                if task:
                    arc_info.set_file_hash(arcpath)
                    db.session.add(arc_info)
                    db.session.commit()

    for part in range(0, parts_num):
        os.remove(dir + os.path.sep + f'part{part + 1}.zip')

    if task:
        send_file_ready_email(task.user, 'Your files is ready.', 'emails/file_ready', errors_list)
        task.progress = f'Files downloaded({files_len}) with {errors_num} fails'
        task.status_code = 4
        task.completed_at = datetime.datetime.now()
        task.unique_process_info = os.path.abspath(arcpath)
        db.session.add(task)
        db.session.commit()
        app_context.pop()
    else:
        app_context.pop()
        return os.path.abspath(arcpath), errors_num


if Config.USE_CELERY:
    from app import celery

    @celery.task
    def download_yt_files_async(playlist: list, task_id=None, dir=None, quality=192, repair_tags=False,
                                send_mails=True):
        return download_yt_files_sync(playlist, task_id=task_id, dir=dir, quality=quality, repair_tags=repair_tags,
                                      send_mails=send_mails)


def download_yt_files(playlist: list, task=None, dir=None, quality=192, repair_tags=False):
    part_size = current_app.config['PLAYLIST_PART_SIZE']
    send_mails = current_app.config['SEND_MAILS']

    if current_app.config['DOWNLOAD_PATH']:
        dir = current_app.config['DOWNLOAD_PATH']
    else:
        dir = dir or os.path.dirname(os.path.realpath(__file__)) + os.path.sep + 'temp'

    kwargs = {'dir': dir,
              'quality': quality,
              'repair_tags': repair_tags,
              'send_mails': send_mails,
              'part_size': part_size}

    if not os.path.isdir(dir):
        os.mkdir(os.path.realpath(dir))

    if task:
        dir += os.path.sep + f'Task{task.id}'

    if not os.path.isdir(dir):
        os.mkdir(os.path.realpath(dir))

    with open(dir + os.path.sep + 'kwargs', 'wb') as file:
        pickle.dump(kwargs, file)

    if task:
        task.progress = 'Waiting'
        db.session.add(task)
        db.session.commit()
        FileInfo.make_records(playlist, task.id)
        arc_info = FileInfo(index=0, file_id='playlist.zip', task_id=task.id)
        db.session.add(arc_info)
        db.session.commit()

    if current_app.config['SYNC_DOWNLOADINGS']:
        app = current_app._get_current_object()
        download_yt_files_sync(playlist, task_id=task.id, quality=quality, dir=dir, repair_tags=repair_tags,
                               send_mails=send_mails, app=app)
    elif current_app.config['USE_CELERY']:
        download_yt_files_async.apply_async(args=[playlist],
                                            kwargs={'task_id': task.id, 'quality': quality, 'dir': dir,
                                                    'repair_tags': repair_tags, 'send_mails': send_mails},
                                            queue='downloading_tasks',
                                            routing_key='download.playlist')
    else:
        Thread(target=download_yt_files_sync,
               args=[playlist],
               kwargs={'task_id': task.id, 'quality': quality, 'dir': dir, 'repair_tags': repair_tags,
                       'send_mails': send_mails}).start()


def get_download_response(filename: str, t: Task, ext='.mp3', end_task=True):
    """Get flask file send response


    :param filename: path to file to send
    :type filename: str
    :param t: task object
    :type t: Task
    :param ext: file extension
    :type ext: str
    """

    if end_task:
        t.progress = 'Done'
        t.status_code = 1
        t.completed_at = datetime.datetime.now()
    db.session.add(t)
    db.session.commit()

    return send_from_directory(os.path.sep.join(os.path.realpath(filename).split(os.path.sep)[:-1]),
                               '.'.join(filename.split(os.sep)[-1].split('.')[:-1]) + ext,
                               as_attachment=True)


def resume_yt_files_downloading_sync(playlist: list, task_id=None, dir=None, quality=192, repair_tags=False,
                                     first_part_index=0, part_size=None):
    app = create_app()
    app_context = app.app_context()
    app_context.push()

    task = Task.query.get(task_id)
    part_size = part_size
    dir = dir or os.path.dirname(os.path.realpath(__file__)) + os.path.sep + 'temp'
    dir += os.path.sep + f'Task{task_id}'
    arcpath = (dir + os.path.sep + 'playlist.zip' or 'playlist.zip')

    working_dir = os.getcwd()
    playlist_offset_left = first_part_index * part_size
    counter = playlist_offset_left
    files_len = len(playlist) + counter
    parts_num = int(files_len / part_size + 1) if files_len % part_size else int(files_len / part_size)
    parts_num += first_part_index

    try:
        arc_info = FileInfo.query.filter_by(file_id='playlist.zip', task_id=task.id).all()[0]
    except IndexError:
        send_file_fail_email(task.user, 'Failed to download your files.', 'emails/file_fail')
        task.force_stop()
        db.session.add(task)
        db.session.commit()
        app_context.pop()
        return

    db.session.add(task)

    errors_list = ['https://www.youtube.com/watch?v=' + file.file_id for file in task.files.all()
                   if file.index != 0 and file.status_code == 2]
    errors_num = len(errors_list)

    for part in range(first_part_index, parts_num):
        try:
            part_info = FileInfo.query.filter_by(index=0, task_id=task.id, file_id=f'part{part + 1}.zip').all()[0]
        except IndexError:
            part_info = FileInfo(index=0, file_id=f'part{part + 1}.zip', task_id=task.id)
            db.session.add(part_info)
            db.session.commit()

        with zipfile.ZipFile(dir + os.path.sep + f'part{part + 1}.zip', 'w') as archive:
            for record in playlist[part*part_size - playlist_offset_left: (part + 1)*part_size - playlist_offset_left]:
                counter += 1
                time.sleep(2)
                file_info = task.files.filter_by(file_id=record).first()

                try:
                    link = 'https://www.youtube.com/watch?v=' + record
                    info = get_yt_file_info(link)
                except BadUrlError:
                    if task:
                        file_info.status_code = 2
                        db.session.add(file_info)
                        db.session.commit()
                    errors_num += 1
                    errors_list.append(link)
                    continue

                if not is_allowed_duration(info):
                    if task:
                        file_info.status_code = 2
                        db.session.add(file_info)
                        db.session.commit()
                    errors_num += 1
                    errors_list.append(link)
                    continue

                task.progress = f'Downloading {counter} of {files_len}'
                db.session.add(task)
                db.session.commit()

                try:
                    filename = download(link, task=None, dir=dir, quality=quality, repair_tags=repair_tags,
                                        log_info=f'Downloading {counter} of {files_len}', )
                    dirname = os.path.dirname(filename)
                    os.chdir(dirname)
                    filename = '.'.join((filename.split(os.sep)[-1].split('.')[:-1])) + '.mp3'
                    archive.write(filename)
                    os.remove(filename)
                    os.chdir(working_dir)

                    file_info.status_code = 1
                    db.session.add(file_info)
                    db.session.commit()

                except youtube_dl.DownloadError:
                    file_info.status_code = 2
                    db.session.add(file_info)
                    db.session.commit()

                    errors_num += 1
                    errors_list.append(link)

        part_info.set_file_hash(dir + os.path.sep + f'part{part + 1}.zip')
        db.session.add(part_info)
        db.session.commit()

    with zipfile.ZipFile(arcpath, 'w') as archive:
        for part in range(0, parts_num):
            with zipfile.ZipFile(dir + os.path.sep + f'part{part + 1}.zip', 'r') as part_:
                extraction_dir = dir + os.path.sep + 'extract'
                os.mkdir(extraction_dir)
                part_.extractall(path=extraction_dir)
                os.chdir(extraction_dir)
                for el in os.listdir('./'):
                    archive.write(el)
                os.chdir(working_dir)
                shutil.rmtree(extraction_dir)

                arc_info.set_file_hash(arcpath)
                db.session.add(arc_info)
                db.session.commit()

    for part in range(0, parts_num):
        os.remove(dir + os.path.sep + f'part{part + 1}.zip')

    send_file_ready_email(task.user, 'Your files is ready.', 'emails/file_ready', errors_list)
    task.progress = f'Files downloaded({files_len}) with {errors_num} fails'
    task.status_code = 4
    task.completed_at = datetime.datetime.now()
    task.unique_process_info = os.path.abspath(arcpath)
    db.session.add(task)
    db.session.commit()
    app_context.pop()


if Config.USE_CELERY:
    from app import celery

    @celery.task
    def resume_yt_files_downloading_async(playlist: list, task_id=None, dir=None, quality=192, repair_tags=False,
                                          first_part_index=0, part_size=None):
        return resume_yt_files_downloading_sync(playlist, task_id=task_id, dir=dir, quality=quality,
                                                repair_tags=repair_tags, first_part_index=first_part_index,
                                                part_size=part_size)


def resume_yt_files_downloading(playlist: list, task=None, dir=None, quality=192, repair_tags=False,
                                first_part_index=0, part_size=None):
    if current_app.config['DOWNLOAD_PATH']:
        dir = current_app.config['DOWNLOAD_PATH']
    if current_app.config['SYNC_DOWNLOADINGS']:
        resume_yt_files_downloading_sync(playlist, task_id=task.id, quality=quality, dir=dir, repair_tags=repair_tags,
                                         first_part_index=0, part_size=None)
    elif current_app.config['USE_CELERY']:
        resume_yt_files_downloading_async.apply_async(args=[playlist],
                                                      kwargs={'task_id': task.id, 'quality': quality, 'dir': dir,
                                                              'repair_tags': repair_tags,
                                                              'first_part_index': first_part_index,
                                                              'part_size': part_size},
                                                      queue='downloading_tasks',
                                                      routing_key='download.playlist')
    else:
        Thread(target=resume_yt_files_downloading_sync,
               args=[playlist],
               kwargs={'task_id': task.id, 'quality': quality, 'dir': dir, 'repair_tags': repair_tags,
                       'first_part_index': first_part_index, 'part_size': part_size}).start()

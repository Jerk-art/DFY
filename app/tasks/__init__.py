from app import create_app
from app import db
from app import mail
from app.models import Task
from app.models import FileInfo
from flask import send_from_directory
from flask import current_app
from flask import render_template
from flask_mail import Message
from requests import get
from threading import Thread
from sqlalchemy.exc import InvalidRequestError
from config import Config

import time
import zipfile
import youtube_dl
import os


def concatenate_elements(list_):
    res = str()
    for i in range(len(list_) - 1):
        res += list_[i]
        res += '.'
    return res


class BadUrlError(Exception):
    pass


def get_yt_file_info(url: str):
    """Request info about youtube video, using google API key specified in config


    :param url: URL to youtube video
    :type url: str

    :returns: dict with value "yt" assigned to key "resource"
              and deserialized json answer from youtube API assigned to key "API_response"
    :rtype: dict
    """

    if url.startswith('https://www.youtube.com/watch?v='):
        vid = url[32:43]
    elif url.startswith('https://youtu.be/'):
        vid = url[17:28]
    else:
        raise BadUrlError('Url do not belong domain yputube.com or does not lead to video.')

    r = get(f'https://www.googleapis.com/youtube/v3/videos?part=contentDetails'
            f'&key={current_app.config["YOUTUBE_API_KEY"]}'
            f'&id={vid}')

    if r.status_code == 200 and r.json()['kind'] and r.json()['items']:
        try:
            kind = r.json()['kind']
            items = r.json()['items']
            if kind != 'youtube#videoListResponse':
                raise BadUrlError('No information about this video.')
            if len(items) == 0:
                raise BadUrlError('No information about this video.')
        except KeyError:
            raise BadUrlError('No information about this video.')
        return {"resource": "yt", "API_response": r.json()}
    elif r.status_code == 200:
        raise BadUrlError('No information about this video.')
    elif r.status_code == 400:
        raise ConnectionError('Bad request, please check your API key.')
    else:
        raise ConnectionError()


def get_sc_file_info(url: str):
    """Request info about soundcloud file, using soundcloud module with API key specified in config


    :param url: URL to soundcloud file
    :type url: str

    :returns: dict with value "sc" assigned to key "resource"
              0 or 1 assigned to key "type" (0 - single file, 1 - playlist item)
              and url assigned to key "url"
    :rtype: dict
    """

    if url.startswith('https://soundcloud.com/'):
        url_splitted = url[8:].split("/")
        url_length = len(url_splitted)
        if url_length == 3 and url_splitted[2] != 'sets':
            r = get(url)
            if r.status_code == 404:
                raise BadUrlError('Audio not found.')
            res = {'type': 0, 'url': url}
        elif url_length == 4 and url_splitted[2] == 'sets':
            r = get(url)
            if r.status_code == 404:
                raise BadUrlError('Audio not found.')
            res = {'type': 1, 'url': url}
        else:
            raise BadUrlError('Url does not lead to audio.')
    else:
        raise BadUrlError('Url do not belong domain soundcloud.com.')
    res['resource'] = "sc"
    return res


def get_yt_playlist_info(pid, max_results=0, page_token=None):
    if page_token:
        r = get(f'https://www.googleapis.com/youtube/v3/playlistItems?part=id%2CcontentDetails'
                f'&maxResults={max_results}'
                f'&pageToken={page_token}'
                f'&playlistId={pid}'
                f'&key={current_app.config["YOUTUBE_API_KEY"]}')
    else:
        r = get(f'https://www.googleapis.com/youtube/v3/playlistItems?part=id%2CcontentDetails'
                f'&maxResults={max_results}'
                f'&playlistId={pid}'
                f'&key={current_app.config["YOUTUBE_API_KEY"]}')
    if r.status_code == 200:
        return r.json()
    elif r.status_code == 400:
        raise ConnectionError('Bad request, please check your API key.')
    elif r.status_code == 404:
        raise BadUrlError('Playlist not found.')
    else:
        raise ConnectionError()


def get_yt_playlist_items(link: str, start_index: int, end_index: int):
    if start_index < 0:
        raise IndexError('First index is out of range.')
    if end_index < start_index:
        raise IndexError('End index is out of range.')
    if link.startswith('https://www.youtube.com/playlist?list='):
        pid = link[38:]
    elif link.startswith('https://www.youtube.com/watch?v=') and len(link) > 80:
        index = link.find('&index=')
        pid = link[49:index]
    else:
        raise BadUrlError('Url do not belong domain youtube.com or does not lead to playlist.')

    res_num = get_yt_playlist_info(pid)['pageInfo']['totalResults']
    if res_num == 0:
        raise BadUrlError('Given playlist is empty.')
    if res_num - 1 < start_index:
        raise IndexError('First index is out of range.')
    if res_num < end_index:
        end_index = res_num

    data = get_yt_playlist_info(pid, max_results=50)

    passed_indexes = 50

    result = list()

    if start_index < 50:
        if end_index < 50:
            for i in range(start_index, end_index):
                result.append(data['items'][i]['contentDetails']['videoId'])
        else:
            for i in range(start_index, 50):
                result.append(data['items'][i]['contentDetails']['videoId'])
            token = data['nextPageToken']
            while True:
                data = get_yt_playlist_info(pid, max_results=50, page_token=token)
                passed_indexes += 50
                if end_index < passed_indexes:
                    for i in range(0, end_index - passed_indexes + 50):
                        result.append(data['items'][i]['contentDetails']['videoId'])
                    break
                else:
                    for i in range(0, 50):
                        result.append(data['items'][i]['contentDetails']['videoId'])
                token = data['nextPageToken']
    else:
        while True:
            token = data['nextPageToken']
            data = get_yt_playlist_info(pid, max_results=50, page_token=token)
            passed_indexes += 50
            if start_index < passed_indexes:
                break
        if end_index < passed_indexes:
            for i in range(start_index - passed_indexes + 50, end_index - passed_indexes + 50):
                result.append(data['items'][i]['contentDetails']['videoId'])
        else:
            for i in range(start_index - passed_indexes + 50, 50):
                result.append(data['items'][i]['contentDetails']['videoId'])
            token = data['nextPageToken']
            while True:
                data = get_yt_playlist_info(pid, max_results=50, page_token=token)
                passed_indexes += 50
                if end_index < passed_indexes:
                    for i in range(0, end_index - passed_indexes + 50):
                        result.append(data['items'][i]['contentDetails']['videoId'])
                    break
                else:
                    for i in range(0, 50):
                        result.append(data['items'][i]['contentDetails']['videoId'])
                token = data['nextPageToken']
    return result


def is_allowed_duration(info: dict):
    """Check video duration to be lower then specified in config(in minutes)


    :param info: The dict obtained from deserialization json answer from youtube or soundcloud API
    :type info: dict

    :returns: True or False
    :rtype: bool
    """
    if info["resource"] == "yt":
        info = info["API_response"]
        try:
            duration = info['items'][0]['contentDetails']['duration']
            if duration.find('H') == -1:
                m_index = duration.find('M')
                if m_index == -1:
                    return True
                else:
                    if int(duration[2:m_index]) <= current_app.config["ALLOWED_DURATION"]:
                        return True
                    else:
                        return False
            else:
                return False
        except Exception as err:
            raise BadUrlError(f"Info is not processed:{info}\nReason:{err}")

    elif info['resource'] == "sc":
        try:
            class Logger:
                def debug(self, msg):
                    pass

                def info(self, msg):
                    pass

                @staticmethod
                def error(msg):
                    print(msg)

            ydl_opts = {'logger': Logger()}

            if info['type'] == 0:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:

                    meta = ydl.extract_info(
                        info['url'],
                        download=False)
                    duration = meta['duration']

                if duration <= current_app.config["ALLOWED_DURATION"] * 60:
                    return True
                else:
                    return False

            elif info['type'] == 1:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:

                    meta = ydl.extract_info(
                        info['url'],
                        download=False)
                    duration = meta["entries"][0]["duration"]

                if duration <= current_app.config["ALLOWED_DURATION"] * 60:
                    return True
                else:
                    return False
        except Exception as err:
            raise BadUrlError(f"Info is not processed:{info}\nReason:{err}")


def download(link: str, task=None, dir=None, quality=192, log_info=None):
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

    dir = dir or os.path.dirname(os.path.realpath(__file__)) + os.path.sep + 'temp'
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
    return filename


def download_yt_files_sync(playlist: list, task=None, dir=None, mode='w', quality=192, app=None):
    dir = dir or os.path.dirname(os.path.realpath(__file__)) + os.path.sep + 'temp'

    if not app:
        app = create_app()
    app_context = app.app_context()
    app_context.push()

    arcpath = (dir + os.path.sep + 'playlist.zip' or 'playlist.zip')
    working_dir = os.getcwd()
    counter = 0
    errors_num = 0
    files_len = len(playlist)

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
        FileInfo.make_records(playlist, task.id)

    with zipfile.ZipFile(arcpath, mode) as archive:
        for record in playlist:
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
                continue

            if not is_allowed_duration(info):
                if task:
                    file_info.status_code = 2
                    db.session.add(file_info)
                    db.session.commit()
                errors_num += 1
                continue

            if task:
                task.progress = f'Downloading {counter} of {files_len}'
                db.session.add(task)
                db.session.commit()

            try:
                filename = download(link, task=None, dir=dir, quality=quality, log_info=f'Downloading {counter} of {files_len}')
                dirname = os.path.dirname(filename)
                os.chdir(dirname)
                filename = concatenate_elements(filename.split(os.sep)[-1].split('.')) + 'mp3'
                archive.write(filename)
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

    if task:
        send_file_ready_email(task.user, 'Your files is ready.', 'emails/file_ready')
        task.progress = f'Files downloaded({files_len}) with {errors_num} fails'
        task.status_code = 4
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
    def download_yt_files_async(playlist: list, task_id=None, dir=None, mode='w', quality=192):
        app = create_app()
        app_context = app.app_context()
        app_context.push()
        task = Task.query.get(task_id)
        app_context.pop()
        return download_yt_files_sync(playlist, task=task, dir=dir, mode=mode, quality=quality, app=app)


def download_yt_files(playlist: list, task=None, dir=None, mode='w', quality=192):
    if current_app.config['USE_CELERY']:
        download_yt_files_async.apply_async(args=[playlist],
                                            kwargs={'task_id': task.id, 'quality': quality, 'dir': dir, 'mode': mode},
                                            queue='downloading_tasks',
                                            routing_key='download.playlist')
    else:
        Thread(target=download_yt_files_sync,
               args=[playlist],
               kwargs={'task': task, 'quality': quality, 'dir': dir, 'mode': mode}).start()


def get_download_response(filename: str, t: Task, ext='mp3', end_task=True):
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
        db.session.add(t)
        db.session.commit()

    return send_from_directory(os.path.dirname(filename),
                               concatenate_elements(filename.split(os.sep)[-1].split('.')) + ext,
                               as_attachment=True)


def create_mail(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    return msg


if Config.USE_CELERY:
    @celery.task
    def send_mail_async(subject, sender, recipients, text_body, html_body):
        app = create_app()
        with app.app_context():
            msg = create_mail(subject, sender, recipients, text_body, html_body)
            mail.send(msg)


def send_mail_sync(subject, sender, recipients, text_body, html_body):
    app = create_app()
    with app.app_context():
        msg = create_mail(subject, sender, recipients, text_body, html_body)
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body, sync=False):
    if sync:
        msg = create_mail(subject, sender, recipients, text_body, html_body)
        mail.send(msg)
    elif current_app.config['USE_CELERY']:
        send_mail_async.apply_async(args=[subject, sender, recipients, text_body, html_body])
    elif current_app.config['ASYNC_TASKS']:
        Thread(target=send_mail_sync, args=(subject, sender, recipients, text_body, html_body)).start()
    else:
        msg = create_mail(subject, sender, recipients, text_body, html_body)
        mail.send(msg)


def send_confirmation_email(user, action, pattern):
    token = user.get_confirmation_token()
    send_email(f'[DFY] {action}',
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template(pattern + '.txt',
                                         user=user, token=token),
               html_body=render_template(pattern + '.html',
                                         user=user, token=token))


def send_file_ready_email(user, action, pattern):
    send_email(f'[DFY] {action}',
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template(pattern + '.txt',
                                         user=user),
               html_body=render_template(pattern + '.html',
                                         user=user),
               sync=True)

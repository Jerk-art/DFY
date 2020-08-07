from app import db
from app import mail
from app.models import Task
from flask import send_from_directory
from flask import current_app
from flask import render_template
from flask_mail import Message
from requests import get
from threading import Thread

import youtube_dl
import os


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
    r = get(f'https://www.googleapis.com/youtube/v3/videos?part=contentDetails&key={current_app.config["YOUTUBE_API_KEY"]}'
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


def download(link: str, t: Task, dir=None):
    """Download file and convert to mp3 using youtube-dl API


    :param link: link to youtube or soundcloud file
    :type link: str
    :param dir: path to directory where should be downloaded file,
                if not specified or None, using temp directory in where placed this .py file
    :type dir: str
    :param t: task object
    :type t: Task

    :returns: path to downloaded file
    :rtype: str
    """

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
            t.progress = 'Converting'
            db.session.add(t)
            db.session.commit()

            nonlocal filename
            filename = d['filename']
        else:
            try:
                print(f'progress: {d["downloaded_bytes"] / d["total_bytes"] * 100:2.2f}%  speed:{d["speed"] / 1000}')
            except TypeError:
                pass

    ydl_opts = {
        'outtmpl': f'{dir}/%(title)s.%(ext)s',
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'logger': Logger(),
        'progress_hooks': [progress_hook],
    }

    print('Downloading')
    t.progress = 'Downloading'
    db.session.add(t)
    db.session.commit()
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])
    return filename


def get_download_response(filename: str, t: Task):
    """Get flask file send response


    :param filename: path to file to send
    :type filename: str
    :param t: task object
    :type t: Task
    """

    def concatenate_elements(list_):
        res = str()
        for i in range(len(list_) - 1):
            res += list_[i]
            res += '.'
        return res

    t.progress = 'Done'
    t.status_code = 1
    db.session.add(t)
    db.session.commit()

    return send_from_directory(os.path.dirname(filename),
                               concatenate_elements(filename.split(os.sep)[-1].split('.')) + 'mp3',
                               as_attachment=True)


def send_mail_async(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if current_app.config['ASYNC_TASKS']:
        Thread(target=send_mail_async, args=(current_app._get_current_object(), msg)).start()
    else:
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

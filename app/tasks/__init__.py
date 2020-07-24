from app import app, db
from app.models import Task
from app.models import TaskError
from flask import send_from_directory
from requests import get
import youtube_dl
import os


class BadUrlError(Exception):
    pass


def get_yt_video_info(url: str):
    """Request info about youtube video, using google API key specified in config


    :param url: URL to youtube video
    :type url: str

    :returns: deserialized json answer from youtube API
    :rtype: dict
    """

    if url.startswith('https://www.youtube.com/watch?v='):
        vid = url[32:43]
    else:
        raise BadUrlError('Url do not belong domain yputube.com or does not lead to video.')
    r = get(f'https://www.googleapis.com/youtube/v3/videos?part=contentDetails&key={app.config["YOUTUBE_API_KEY"]}'
            f'&id={vid}')
    # print(r.status_code)
    # print(r.json())
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
        return r.json()
    elif r.status_code == 200:
        raise BadUrlError('No information about this video.')
    elif r.status_code == 400:
        raise ConnectionError('Bad request, please check your API key.')
    else:
        raise ConnectionError()


def is_allowed_duration(info: dict):
    """Check video duration to be lower then specified in config(in minutes)


    :param info: The dict obtained from deserialization json answer from youtube or soundcloud API
    :type info: dict

    :returns: True or False
    :rtype: bool
    """

    try:
        duration = info['items'][0]['contentDetails']['duration']
        if duration.find('H') == -1:
            m_index = duration.find('M')
            if m_index == -1:
                return True
            else:
                if int(duration[2:m_index]) <= app.config["ALLOWED_DURATION"]:
                    return True
                else:
                    return False
        else:
            return False
    except Exception as err:
        raise BadUrlError(f"Info is not processed:{info}\nReason:{err}")


def download(link: str, ip: str, dir=None):
    """Download file and convert to mp3 using youtube-dl API


    :param link: link to youtube or soundcloud file
    :type link: str
    :param ip: ip of the user who started downloading
    :type ip: str
    :param dir: path to directory where should be downloaded file,
                if not specified or None, using temp directory in where placed this .py file
    :type dir: str
    :returns: path to downloaded file, task object
    :rtype: tuple with string and Task object
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
    t = Task.query.filter_by(user_ip=ip, status_code=0).first()
    if not t:
        raise TaskError('No such task in database')
    t.progress = 'Downloading'
    db.session.add(t)
    db.session.commit()
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])
    return filename, t


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


# if __name__ == '__main__':
#     info = get_yt_video_info('https://www.youtube.com/watch?v=6_qbEsfJ4_8&list=PLk_klgt4LMVdcHAKqQ93bKtQ_r2YgsxlP&index=2')
#     print(is_allowed_duration(info))
#     pass

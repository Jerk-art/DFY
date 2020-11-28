from flask import current_app
from requests import get

import youtube_dl


class BadUrlError(Exception):
    pass


def get_yt_file_info(url: str):
    """Request info about youtube video, using google API key specified in config


    :param url: URL to youtube video
    :type url: str

    :raises BadUrlError: when no information is received about the video from API
    :raises ConnectionError: when status code not 200

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
        raise ConnectionError(f'{r.status_code} - {r.json()["error"]["message"]}')


def get_sc_file_info(url: str):
    """Request info about soundcloud file, using soundcloud module with API key specified in config


    :param url: URL to soundcloud file
    :type url: str

    :raises BadUrlError: when there is no information on request

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
    """Request info about youtube playlist using google API key specified in config


    :param pid: youtube playlist id
    :type pid: str
    :param max_results: max results
    :type max_results: int
    :param page_token: token of page to be received
    :type page_token: str

    :raises ValueError: when max_results > 50
    :raises BadUrlError: when no information is received from API
    :raises ConnectionError: when status code not 200

    :returns: deserialized json response as dict from API
    :rtype: dict
    """
    if max_results > 50:
        return ValueError(f'Maximum is 50 results, but requested {max_results}')
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
        raise ConnectionError(f'{r.status_code} - {r.json()["error"]["message"]}')


def get_yt_playlist_items(link: str, start_index: int, end_index: int):
    """Request playlist items with indexes in range specified by params start_index end end_index
       In case when last index is greater than len of playlist it will be overridden with len value


    :param link: link to youtube playlist
    :type link: str
    :param start_index: first index of range
    :type start_index: int
    :param end_index: last index of range
    :type end_index: int

    :raises BadUrlError: when playlist is empty
    :raises IndexError: when first index is out of range

    :returns: deserialized json response as dict from API
    :rtype: dict
    """
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

    :raises BadUrlError: when any other exception is occured

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

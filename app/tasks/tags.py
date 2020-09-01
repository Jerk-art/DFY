from requests import get
from requests import post
from flask import current_app
from mutagen.id3 import ID3, TIT2, TALB, TPE1, APIC, TRCK, TDRC, ID3NoHeaderError
from simplejson import JSONDecodeError

import base64
import time


def get_yt_video_tags(id):
    r = get(f'https://www.googleapis.com/youtube/v3/videos?part=snippet'
            f'&key={current_app.config["YOUTUBE_API_KEY"]}'
            f'&id={id}')
    info = r.json()
    video_title = info['items'][0]['snippet']['title']
    channel_title = info['items'][0]['snippet']['channelTitle']
    thumbnail_url = info['items'][0]['snippet']['thumbnails']['default']['url']
    return channel_title, video_title, thumbnail_url


def get_sc_file_tags(url: str):
    class Logger:
        def debug(self, msg):
            pass

        def info(self, msg):
            pass

        @staticmethod
        def error(msg):
            print(msg)

    ydl_opts = {'logger': Logger()}

    import youtube_dl
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:

        meta = ydl.extract_info(
            url,
            download=False)
    return meta['uploader'], meta['title'], meta['thumbnails'][0]['url']


def get_repaired_audio_tags(channel_title, video_title):

    def capitalize_all_words(s: str):
        res = str()
        for el in s.split(' '):
            if el == ' ' or len(el) == 0:
                continue
            res += ' ' + el.capitalize()
        return res[1:]

    quote1_index = video_title.find('"')
    quote2_index = video_title.find('"', quote1_index + 1)

    if quote1_index > -1:
        if quote2_index > 0:
            video_title = video_title.replace('"', '')

    i1 = video_title.find('(')
    if i1 > -1 and (i1 < quote1_index - 1 or i1 > quote2_index - 2):
        i2 = video_title.find(')')
        if i2 > 0:
            title = video_title[:i1]
            title += video_title[i2 + 1:]
            video_title = title

    i1 = video_title.find('[')
    if i1 > -1 and (i1 < quote1_index - 1 or i1 > quote2_index - 2):
        i2 = video_title.find(']')
        if i2 > 0:
            title = video_title[:i1]
            title += video_title[i2 + 1:]
            video_title = title

    # '-' and '–' are different symbols!
    video_title = video_title.split('-')
    if len(video_title) == 1:
        video_title = video_title[0].split('–')
        if len(video_title) == 1:
            video_title = video_title[0].split(':')

    if len(video_title) > 1:
        artist = video_title[0].strip()
        title = '-'.join(video_title[1:]).strip().strip(' -')
    else:
        artist = channel_title.replace('VEVO', '').replace(' - Topic', '').strip()
        title = video_title[0].strip()

    artist = capitalize_all_words(artist).replace('_', ' ').replace('-', ' ')
    title = capitalize_all_words(title)

    return artist, title


def get_spotify_auth_token():
    info = base64.b64encode(f"{current_app.config['SPOTIFY_UID']}:{current_app.config['SPOTIFY_SECRET']}".encode()).decode()
    r = post('https://accounts.spotify.com/api/token',
             headers={'Authorization': f'Basic {info}'},
             data={'grant_type': 'client_credentials'})
    token = r.json()['access_token']
    return token


class ReparationError(Exception):
    pass


def get_repaired_tags_from_spotify(token, artist, title):
    result = {}
    r = get(f'https://api.spotify.com/v1/search?q=artist%3A{artist.replace(" ", "%20")}'
             f'%20track%3A{title.replace(" ", "%20")}'
             f'&type=track'
             f'&limit=1',
             headers={'Accept': 'application/json',
                      'Content-Type': 'application_json',
                      'Authorization': f'Bearer {token}'})
    tags = r.json()
    if tags['tracks']['items']:
        if tags['tracks']['items'][0]['album']['album_type'] == 'album':
            result['album'] = tags['tracks']['items'][0]['album']['name']
            result['artist'] = tags['tracks']['items'][0]['album']['artists'][0]['name']
            if title.lower() in tags['tracks']['items'][0]['name'].lower():
                result['title'] = tags['tracks']['items'][0]['name']
                result['image'] = tags['tracks']['items'][0]['album']['images'][0]['url']
                result['release_date'] = tags['tracks']['items'][0]['album']['release_date']
                result['number'] = tags['tracks']['items'][0]['track_number']
            else:
                r = get(f'https://api.spotify.com/v1/search?q=artist%3A{artist.replace(" ", "%20")}'
                        f'%20track%3A{title.replace(" ", "%20")}'
                        f'&type=track'
                        f'&limit=50',
                        headers={'Accept': 'application/json',
                                 'Content-Type': 'application_json',
                                 'Authorization': f'Bearer {token}'})
                tags = r.json()
                i = 0
                res_len = len(tags['tracks']['items'])
                for el in tags['tracks']['items']:
                    if title.lower() in el['name'].lower():
                        break
                    else:
                        if i == res_len - 1:
                            raise ReparationError('Failed to find such track')
                    i += 1
                result['title'] = tags['tracks']['items'][i]['name']
                result['image'] = tags['tracks']['items'][i]['album']['images'][0]['url']
                result['release_date'] = tags['tracks']['items'][i]['album']['release_date']
                result['number'] = tags['tracks']['items'][i]['track_number']
        else:
            result['artist'] = tags['tracks']['items'][0]['album']['artists'][0]['name']
            result['title'] = tags['tracks']['items'][0]['name']
            result['image'] = tags['tracks']['items'][0]['album']['images'][0]['url']
            result['release_date'] = tags['tracks']['items'][0]['album']['release_date']
    else:
        raise ReparationError('Failed to find such track')
    return result


def get_artist_tags_from_spotify(token, artist):
    result = {}
    r = get(f'https://api.spotify.com/v1/search?q=artist%3A{artist.replace(" ", "%20")}'
            f'&type=artist'
            f'&limit=1',
            headers={'Accept': 'application/json',
                     'Content-Type': 'application_json',
                     'Authorization': f'Bearer {token}'})
    tags = r.json()
    if tags['artists']['items']:
        result['artist'] = artist
        result['image'] = tags['artists']['items'][0]['images'][0]['url']
    else:
        raise ReparationError('Failed to find such track')
    return result


def get_repaired_tags_from_itunes(artist, title):
    result = {}
    r = get(f'https://itunes.apple.com/search?term={"+".join(artist.split(" "))}+{"+".join(title.split(" "))}'
            f'&media=music'
            f'&limit=1')
    try:
        tags = r.json()
    except JSONDecodeError:
        time.sleep(2)
        r = get(f'https://itunes.apple.com/search?term={"+".join(artist.split(" "))}+{"+".join(title.split(" "))}'
                f'&media=music'
                f'&limit=1')
        try:
            tags = r.json()
        except JSONDecodeError:
            return
    if tags['resultCount']:
        if tags['results'][0]['collectionName'].endswith('Single'):
            result['artist'] = tags['results'][0]['artistName']
            result['title'] = tags['results'][0]['trackName']
            result['image'] = tags['results'][0]['artworkUrl100']
            result['release_date'] = tags['results'][0]['releaseDate']
        else:
            result['album'] = tags['results'][0]['collectionName']
            result['artist'] = tags['results'][0]['artistName']
            if tags['results'][0]['trackName'].lower() == title.lower():
                result['title'] = tags['results'][0]['trackName']
                result['image'] = tags['results'][0]['artworkUrl100']
                result['release_date'] = tags['results'][0]['releaseDate']
                result['number'] = tags['results'][0]['trackNumber']
            else:
                r = get(
                    f'https://itunes.apple.com/search?term={"+".join(artist.split(" "))}+{"+".join(title.split(" "))}'
                    f'&media=music'
                    f'&limit=50')
                try:
                    tags = r.json()
                except JSONDecodeError:
                    time.sleep(2)
                    r = get(
                        f'https://itunes.apple.com/search?term={"+".join(artist.split(" "))}+{"+".join(title.split(" "))}'
                        f'&media=music'
                        f'&limit=50')
                    try:
                        tags = r.json()
                    except JSONDecodeError:
                        return
                i = 0
                res_len = len(tags['results'])
                for el in tags['results']:
                    if title.lower() in el['trackName'].lower():
                        break
                    else:
                        if i == res_len - 1:
                            raise ReparationError('Failed to find such track')
                    i += 1
                result['title'] = tags['results'][i]['trackName']
                result['image'] = tags['results'][i]['artworkUrl100']
                result['release_date'] = tags['results'][i]['releaseDate']
                result['number'] = tags['results'][i]['trackNumber']
    else:
        raise ReparationError('Failed to find such track')
    return result


def get_repaired_tags_for_yt(id):
    video_tags = get_yt_video_tags(id)
    primary_tags = get_repaired_audio_tags(video_tags[0], video_tags[1])
    result = {}
    token = get_spotify_auth_token()
    try:
        result = get_repaired_tags_from_spotify(token, primary_tags[0], primary_tags[1])
    except ReparationError:
        try:
            result = get_repaired_tags_from_itunes(primary_tags[0], primary_tags[1])
        except ReparationError:
            try:
                result = get_artist_tags_from_spotify(token, primary_tags[0])
                result['title'] = primary_tags[1]
            except ReparationError:
                result['artist'] = primary_tags[0]
                result['title'] = primary_tags[1]
                result['image'] = video_tags[2]
    return result


def get_repaired_tags_for_sc(url):
    video_tags = get_sc_file_tags(url)
    primary_tags = get_repaired_audio_tags(video_tags[0], video_tags[1])
    result = {}
    token = get_spotify_auth_token()
    try:
        result = get_repaired_tags_from_spotify(token, primary_tags[0], primary_tags[1])
    except ReparationError:
        try:
            result = get_repaired_tags_from_itunes(primary_tags[0], primary_tags[1])
        except ReparationError:
            try:
                result = get_artist_tags_from_spotify(token, primary_tags[0])
                result['title'] = primary_tags[1]
            except ReparationError:
                result['artist'] = primary_tags[0]
                result['title'] = primary_tags[1]
                result['image'] = video_tags[2]
    return result


def get_image_bytes_from_url(url):
    return get(url, stream=True).raw.read()


def insert_tags(filepath, tags):
    try:
        file = ID3(filepath)
    except ID3NoHeaderError:
        file = ID3()
    for key in tags:
        if key == 'album':
            file['TALB'] = TALB(encoding=3, text=tags[key])
        elif key == 'artist':
            file['TPE1'] = TPE1(encoding=3, text=tags[key])
        elif key == 'title':
            file['TIT2'] = TIT2(encoding=3, text=tags[key])
        elif key == 'image':
            file.add(APIC(3, 'image/jpeg', 3, 'Front cover', get_image_bytes_from_url(tags[key])))
        elif key == 'release_date':
            file['TDRC'] = TDRC(encoding=3, text=tags[key])
        elif key == 'number':
            file['TRCK'] = TRCK(encoding=3, text=str(tags[key]))
    file.save(filepath)

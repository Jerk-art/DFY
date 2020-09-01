from app import db, create_app
from app.models import User
from app.tasks.info import *
from app.tasks.download import download
from app.tasks.download import download_yt_files_sync
from app.tasks.tags import *
from config import Config

import pytest
import os
import shutil


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    USE_CELERY = False
    SEND_MAILS = False


app = create_app(TestConfig)

TEMP_DIR = f'.{os.path.sep}tests{os.path.sep}temp'


@pytest.fixture
def client():
    with app.test_client() as client:
        app_context = app.app_context()
        app_context.push()
        db.create_all()
        u = User()
        u.username = 'user'
        u.email = 'user@example.com'
        u.set_password_hash('12345678')
        db.session.add(u)
        db.session.commit()
        yield client

    db.session.remove()
    db.drop_all()
    app_context.pop()

    try:
        shutil.rmtree(TEMP_DIR)
    except FileNotFoundError:
        pass


# Testing get info


def test_get_yt_file_info(client):
    info = get_yt_file_info("https://www.youtube.com/watch?v=rTyKk53Wq3w")
    assert info['resource'] == 'yt'
    assert len(info['API_response']['items']) > 0
    assert 'duration' in info['API_response']['items'][0]['contentDetails']

    info = get_yt_file_info("https://youtu.be/JR6aKhnAcFA")
    assert info['resource'] == 'yt'
    assert len(info['API_response']['items']) > 0
    assert 'duration' in info['API_response']['items'][0]['contentDetails']

    info = get_yt_file_info('https://www.youtube.com/watch?v=rTyKk53Wq3w&list=PLk_klgt4LMVdcHAKqQ93bKtQ_r2YgsxlP')
    assert info['resource'] == 'yt'
    assert len(info['API_response']['items']) > 0
    assert 'duration' in info['API_response']['items'][0]['contentDetails']

    with pytest.raises(BadUrlError, match='No information about this video.'):
        get_yt_file_info('https://www.youtube.com/watch?v=rTyKk53Wq3s')

    with pytest.raises(BadUrlError, match='Url do not belong domain yputube.com or does not lead to video.'):
        get_yt_file_info('https://www.yutube.com/watch?v=rTyKk53Wq3s')

    with pytest.raises(BadUrlError, match='No information about this video.'):
        get_yt_file_info('https://www.youtube.com/watch?v=rTyKk5')


def test_get_sc_file_info(client):
    info = get_sc_file_info("https://soundcloud.com/elinacooper/"
                            "bring-me-the-horizon-nihilist-bluescover-by-the-veer-union")
    assert info['resource'] == 'sc'
    assert info['type'] == 0

    info = get_sc_file_info('https://soundcloud.com/bluestahli/sets/lakes-of-flame-comaduster')
    assert info['resource'] == 'sc'
    assert info['type'] == 1

    with pytest.raises(BadUrlError, match='Url do not belong domain soundcloud.com.'):
        get_sc_file_info('https://soundloud.com/bluestahli/sets/lakes-of-flame-comaduste')

    with pytest.raises(BadUrlError, match='Audio not found.'):
        get_sc_file_info('https://soundcloud.com/bluestahli/sets/lakes-of-flame-comaduste')


def test_get_yt_playlist_info(client):
    data = get_yt_playlist_info("OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA")
    assert data['pageInfo']['totalResults'] == 14

    with pytest.raises(BadUrlError, match='Playlist not found.'):
        get_yt_playlist_info('OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijf')


# Testing get playlist items


def test_get_yt_playlist_items(client):
    with pytest.raises(BadUrlError, match='Url do not belong domain youtube.com or does not lead to playlist.'):
        get_yt_playlist_items('https://www.youtubed.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA', 0, 0)

    with pytest.raises(IndexError, match='First index is out of range.'):
        get_yt_playlist_items('https://www.youtube.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA', -1, 0)

    with pytest.raises(IndexError, match='End index is out of range.'):
        get_yt_playlist_items('https://www.youtube.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA', 0, -1)

    with pytest.raises(IndexError, match='First index is out of range.'):
        get_yt_playlist_items('https://www.youtube.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA', 14, 14)

    playlist = get_yt_playlist_items('https://www.youtube.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA', 0, 13)
    assert len(playlist) == 13

    playlist = get_yt_playlist_items('https://www.youtube.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA', 0, 14)
    assert len(playlist) == 14
    assert playlist[0] == 'XkCA2XqUJ4o'
    assert playlist[13] == 'uX3Gw82f6GU'

    playlist = get_yt_playlist_items('https://www.youtube.com/playlist?list=PL6Lt9p1lIRZ311J9ZHuzkR5A3xesae2pk', 50, 51)
    assert len(playlist) == 1
    assert playlist[0] == 'O-fyNgHdmLI'

    playlist = get_yt_playlist_items('https://www.youtube.com/playlist?list=PL6Lt9p1lIRZ311J9ZHuzkR5A3xesae2pk', 69, 131)
    assert len(playlist) == 62
    assert playlist[0] == '8IEQpfA528M'
    assert playlist[61] == 'Y6ljFaKRTrI'


# Testing download module


def test_download_from_yt(client):
    try:
        os.mkdir(TEMP_DIR)
    except FileExistsError:
        pass
    filename = download('https://www.youtube.com/watch?v=rTyKk53Wq3w', dir=TEMP_DIR)
    filename = os.path.dirname(filename) + os.path.sep + \
               '.'.join(filename.split(os.sep)[-1].split('.')[:-1]) + '.mp3'
    assert os.path.isfile(filename) is True


def test_download_from_sc(client):
    try:
        os.mkdir(TEMP_DIR)
    except FileExistsError:
        pass
    filename = download('https://soundcloud.com/elinacooper/'
                        'bring-me-the-horizon-nihilist-bluescover-by-the-veer-union', dir=TEMP_DIR)
    filename = os.path.dirname(filename) + os.path.sep + \
               '.'.join(filename.split(os.sep)[-1].split('.')[:-1]) + '.mp3'
    assert os.path.isfile(filename) is True


def test_download_yt_files(client):
    try:
        os.mkdir(TEMP_DIR)
    except FileExistsError:
        pass
    l = get_yt_playlist_items('https://www.youtube.com/playlist?list=PLk_klgt4LMVdcHAKqQ93bKtQ_r2YgsxlP', 0, 2)
    path = download_yt_files_sync(l, dir=TEMP_DIR)
    assert os.path.isfile(path[0]) is True


# Testing tags module


def test_get_yt_video_tags(client):
    tags = get_yt_video_tags('keMBtyjYUPQ')
    assert tags[0] == 'starsetonline'
    assert tags[1] == 'STARSET - PERFECT MACHINE (Official Audio)'
    assert tags[2] == 'https://i.ytimg.com/vi/keMBtyjYUPQ/default.jpg'


def test_get_sc_file_tags(client):
    tags = get_sc_file_tags('https://soundcloud.com/bluestahli/the-devil')
    assert tags[0] == 'Blue_Stahli'
    assert tags[1] == 'The Devil'
    assert tags[2] is not None


def test_get_repaired_video_tags(client):
    tags = get_repaired_audio_tags('starsetonline', 'STARSET - PERFECT MACHINE (Official Audio)')
    assert tags[0] == 'Starset'
    assert tags[1] == 'Perfect Machine'

    tags = get_repaired_audio_tags('starsetonline', 'PERFECT MACHINE (Official Audio)')
    assert tags[0] == 'Starsetonline'
    assert tags[1] == 'Perfect Machine'


def test_get_spotify_auth_token(client):
    assert get_spotify_auth_token() is not None


def test_get_repaired_tags_from_spotify(client):
    token = get_spotify_auth_token()
    tags = get_repaired_tags_from_spotify(token, 'STARSET', 'PERFECT MACHINE')
    assert tags['album'] is not None
    tags = get_repaired_tags_from_spotify(token, 'The Pretty Reckless', 'Death By Rock And Roll')
    assert tags.get('album') is None


def test_get_artist_tags_from_spotify(client):
    token = get_spotify_auth_token()
    tags = get_artist_tags_from_spotify(token, 'Chevelle')
    assert tags['artist'] == 'Chevelle'


def test_get_repaired_tags_from_itunes(client):
    tags = get_repaired_tags_from_itunes('STARSET', 'PERFECT MACHINE')
    assert tags['album'] is not None
    tags = get_repaired_tags_from_itunes('The Pretty Reckless', 'Death By Rock And Roll')
    assert tags.get('album') is None
    tags = get_repaired_tags_from_itunes('Epica', 'Design Your Universe')
    assert tags['album'] == 'Design Your Universe'
    assert 'Design Your Universe' in tags['title']
    assert tags['number'] == 13


def test_get_repaired_tags_for_yt(client):
    tags = get_repaired_tags_for_yt('dhZTNgAs4Fc')
    assert tags['album'] is not None
    tags = get_repaired_tags_for_yt('DpSARXWyCO4')
    assert tags['artist'] == 'Starxfox2772'
    tags = get_repaired_tags_for_yt('BX6KILafIS0')
    assert tags['title'] == 'Death By Rock And Roll'


def test_get_repaired_tags_for_sc(client):
    tags = get_repaired_tags_for_sc('https://soundcloud.com/bluestahli/the-devil')
    assert 'The Devil' in tags['album']
    assert 'The Devil' in tags['title']


def test_insert_tags(client):
    try:
        os.mkdir(TEMP_DIR)
    except FileExistsError:
        pass
    filename = download('https://www.youtube.com/watch?v=DpSARXWyCO4', dir=TEMP_DIR)
    filepath = os.path.dirname(filename) + os.path.sep + \
               '.'.join(filename.split(os.sep)[-1].split('.')[:-1]) + '.mp3'
    assert os.path.isfile(filepath) is True
    tags = get_repaired_tags_for_yt('DpSARXWyCO4')
    insert_tags(filepath, tags)
    file = ID3(filepath)
    assert file.getall('APIC')[0] == APIC(3, 'image/jpeg', 3, 'Front cover', get_image_bytes_from_url(tags['image']))

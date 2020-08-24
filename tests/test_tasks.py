import pytest
import os
import shutil

from app import create_app, db
from app.models import User
from app.tasks import BadUrlError
from app.tasks import get_yt_file_info
from app.tasks import get_sc_file_info
from app.tasks import get_yt_playlist_info
from app.tasks import get_yt_playlist_items
from app.tasks import concatenate_elements
from app.tasks import download
from app.tasks import download_yt_files_sync
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False
    USE_CELERY = False


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


@pytest.fixture
def client2():
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
    assert playlist[61] == 'EqkBRVukQmE'


# Testing download


def test_download_from_yt(client):
    try:
        os.mkdir(TEMP_DIR)
    except FileExistsError:
        pass
    filename = download('https://www.youtube.com/watch?v=rTyKk53Wq3w', dir=TEMP_DIR)
    filename = os.path.dirname(filename) + os.path.sep + \
               concatenate_elements(filename.split(os.sep)[-1].split('.')) + 'mp3'
    assert os.path.isfile(filename) is True


def test_download_from_sc(client):
    try:
        os.mkdir(TEMP_DIR)
    except FileExistsError:
        pass
    filename = download('https://soundcloud.com/elinacooper/'
                        'bring-me-the-horizon-nihilist-bluescover-by-the-veer-union', dir=TEMP_DIR)
    filename = os.path.dirname(filename) + os.path.sep + \
               concatenate_elements(filename.split(os.sep)[-1].split('.')) + 'mp3'
    assert os.path.isfile(filename) is True


def test_download_yt_files(client2):
    try:
        os.mkdir(TEMP_DIR)
    except FileExistsError:
        pass
    l = get_yt_playlist_items('https://www.youtube.com/playlist?list=PLk_klgt4LMVdcHAKqQ93bKtQ_r2YgsxlP', 0, 2)
    path = download_yt_files_sync(l, dir=TEMP_DIR)
    os.path.isfile(path[0])

import pytest
import os
import shutil
import time

from app import create_app, db
from app.models import Task
from app.tasks import BadUrlError
from app.tasks import get_yt_file_info
from app.tasks import get_sc_file_info
from app.tasks import download
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'


app = create_app(TestConfig)


@pytest.fixture
def client():
    with app.test_client() as client:
        app_context = app.app_context()
        app_context.push()
        db.create_all()
        yield client

    db.session.remove()
    db.drop_all()
    app_context.pop()


def test_db(client):
    t = Task(description='Downloading mp3', user_ip='127', status_code=0, progress='Waiting')
    db.session.add(t)
    db.session.commit()
    assert len(Task.query.all()) == 1


# Testing get_yt_file_info

def test_get_yt_file_info_with_common_video(client):
    info = get_yt_file_info("https://www.youtube.com/watch?v=rTyKk53Wq3w")
    assert info['resource'] == 'yt'
    assert len(info['API_response']['items']) > 0
    assert 'duration' in info['API_response']['items'][0]['contentDetails']


def test_get_yt_file_info_with_playlist_item(client):
    info = get_yt_file_info('https://www.youtube.com/watch?v=rTyKk53Wq3w&list=PLk_klgt4LMVdcHAKqQ93bKtQ_r2YgsxlP')
    assert info['resource'] == 'yt'
    assert len(info['API_response']['items']) > 0
    assert 'duration' in info['API_response']['items'][0]['contentDetails']


def test_get_yt_file_info_with_non_accessible(client):
    with pytest.raises(BadUrlError, match='No information about this video.'):
        get_yt_file_info('https://www.youtube.com/watch?v=rTyKk53Wq3s')


def test_get_yt_file_info_with_bad_url(client):
    with pytest.raises(BadUrlError, match='Url do not belong domain yputube.com or does not lead to video.'):
        get_yt_file_info('https://www.yutube.com/watch?v=rTyKk53Wq3s')


def test_get_yt_file_info_with_bad_id(client):
    with pytest.raises(BadUrlError, match='No information about this video.'):
        get_yt_file_info('https://www.youtube.com/watch?v=rTyKk5')


# Testing get_sc_file_info

def test_get_sc_file_info_with_common_video(client):
    info = get_sc_file_info("https://soundcloud.com/elinacooper/"
                            "bring-me-the-horizon-nihilist-bluescover-by-the-veer-union")
    assert info['resource'] == 'sc'
    assert info['type'] == 0


def test_get_sc_file_info_with_playlist_item(client):
    info = get_sc_file_info('https://soundcloud.com/bluestahli/sets/lakes-of-flame-comaduster')
    assert info['resource'] == 'sc'
    assert info['type'] == 1


def test_get_sc_file_info_with_bad_url(client):
    with pytest.raises(BadUrlError, match='Url do not belong domain soundcloud.com.'):
        get_sc_file_info('https://soundloud.com/bluestahli/sets/lakes-of-flame-comaduste')


def test_get_sc_file_info_with_bad_id(client):
    with pytest.raises(BadUrlError, match='Audio not found.'):
        get_sc_file_info('https://soundcloud.com/bluestahli/sets/lakes-of-flame-comaduste')


# Testing download

def test_download_from_yt(client):
    def concatenate_elements(list_):
        res = str()
        for i in range(len(list_) - 1):
            res += list_[i]
            res += '.'
        return res

    t = Task(description="Downloading mp3", user_ip='None', status_code=0, progress='Waiting')
    db.session.add(t)
    db.session.commit()
    try:
        os.mkdir('temp')
    except FileExistsError:
        pass
    filename = download('https://www.youtube.com/watch?v=rTyKk53Wq3w', t, dir='./temp')
    filename = os.path.dirname(filename) + os.path.sep + \
               concatenate_elements(filename.split(os.sep)[-1].split('.')) + 'mp3'
    assert t.progress == 'Converting'
    assert os.path.isfile(filename) is True
    try:
        shutil.rmtree('./temp')
    except FileNotFoundError:
        pass


def test_download_from_sc(client):
    def concatenate_elements(list_):
        res = str()
        for i in range(len(list_) - 1):
            res += list_[i]
            res += '.'
        return res

    t = Task(description="Downloading mp3", user_ip='None', status_code=0, progress='Waiting')
    db.session.add(t)
    db.session.commit()
    try:
        os.mkdir('temp')
    except FileExistsError:
        pass
    filename = download('https://soundcloud.com/elinacooper/'
                        'bring-me-the-horizon-nihilist-bluescover-by-the-veer-union', t, dir='./temp')
    filename = os.path.dirname(filename) + os.path.sep + \
               concatenate_elements(filename.split(os.sep)[-1].split('.')) + 'mp3'
    assert t.progress == 'Converting'
    assert os.path.isfile(filename) is True
    try:
        shutil.rmtree('./temp')
    except FileNotFoundError:
        pass


try:
    shutil.rmtree('./temp')
except FileNotFoundError:
    pass

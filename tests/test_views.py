from app import create_app, db
from app.models import User
from app.tasks.tags import get_repaired_tags_for_yt
from app.tasks.tags import get_repaired_tags_for_sc
from app.tasks.tags import ID3, TIT2
from config import Config

import time
import pytest
import shutil
import os


TEMP_DIR = f'.{os.path.sep}tests{os.path.sep}temp'


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    USE_CELERY = False
    SEND_MAILS = False
    SYNC_DOWNLOADINGS = True
    DOWNLOAD_PATH = TEMP_DIR


app = create_app(TestConfig)

@pytest.fixture
def client():
    try:
        os.mkdir(TEMP_DIR)
    except FileExistsError:
        pass
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


def test_index_view(client):
    r = client.get('/')
    assert r.status_code == 200
    r = client.get('/index')
    assert r.status_code == 200


def test_index_view_authorized(client):
    u = User.query.get(1)
    u.confirmed = True
    db.session.add(u)
    db.session.commit()

    client.post('/sign_in', data=dict(username='user',
                                      email='user@example.com',
                                      password='12345678'),
                follow_redirects=True)
    r = client.get('/index')
    assert b'Quality' in r.data
    assert b'Tag it' in r.data


def test_get_progress_view(client):
    r = client.get('/get_progress')
    assert r.status_code == 200
    data = r.get_json()
    assert data['Status_code'] == 1
    assert data['Progress'] == 'Done'


def test_download_yt_view(client):
    r = client.get('/download_yt')
    assert r.status_code == 302
    r = client.post('/download_yt', data=dict(link='https://www.youtube.com/watch?v=nMUyqlTR_4'))
    assert r.status_code == 302
    r = client.post('/download_yt', data=dict(link='https://www.youtube.com/watch?v=nMUyQqlTR_4'))
    assert r.status_code == 200


def test_download_sc_view(client):
    r = client.get('/download_sc')
    assert r.status_code == 302
    r = client.post('/download_sc', data=dict(link='https://soundcloud.com/elinacooper/'
                                                   'bring-me-the-horizon-nihilist-bluescver-by-the-veer-union'))
    assert r.status_code == 302
    r = client.post('/download_sc', data=dict(link='https://soundcloud.com/elinacooper/'
                                                   'bring-me-the-horizon-nihilist-bluescover-by-the-veer-union'))
    assert r.status_code == 200


def test_download_yt_view_authorized(client):
    u = User.query.get(1)
    u.confirmed = True
    db.session.add(u)
    db.session.commit()

    client.post('/sign_in', data=dict(username='user',
                                      email='user@example.com',
                                      password='12345678'),
                follow_redirects=True)
    sep = os.path.sep
    client.post('/download_yt', data=dict(link='https://www.youtube.com/watch?v=nMUyQqlTR_4', repair_tags=True))
    filepath = f'{TEMP_DIR}{sep}Task1{sep}' + 'NINE LASHES - Rise (Official Lyric Video).mp3'
    file = ID3(filepath)
    tags = get_repaired_tags_for_yt('nMUyQqlTR_4')
    assert file.getall('TIT2')[0] == TIT2(encoding=3, text=tags['title'])
    os.remove(filepath)


def test_download_sc_view_authorized(client):
    u = User.query.get(1)
    u.confirmed = True
    db.session.add(u)
    db.session.commit()

    client.post('/sign_in', data=dict(username='user',
                                      email='user@example.com',
                                      password='12345678'),
                follow_redirects=True)

    client.post('/download_sc', data=dict(link='https://soundcloud.com/bluestahli/the-devil', repair_tags=True))
    sep = os.path.sep
    filepath = f'{TEMP_DIR}{sep}Task1{sep}' + 'The Devil.mp3'
    file = ID3(filepath)
    tags = get_repaired_tags_for_sc('https://soundcloud.com/bluestahli/the-devil')
    assert file.getall('TIT2')[0] == TIT2(encoding=3, text=tags['title'])
    os.remove(filepath)


def test_download_playlist_items_view(client):
    r = client.get('download_playlist_items', follow_redirects=True)
    assert b'Download' in r.data

    r = client.post('download_playlist_items', follow_redirects=True)
    assert b'Download' in r.data

    u = User.query.get(1)
    u.confirmed = True
    db.session.add(u)
    db.session.commit()

    client.post('/sign_in', data=dict(username='user',
                                      email='user@example.com',
                                      password='12345678'),
                follow_redirects=True)

    r = client.get('download_playlist_items', follow_redirects=True)
    assert b'First item' in r.data

    client.post('/download_playlist_items',
                data=dict(link='https://www.youtube.com/playlist?list=OLAK5uy_kf2mr4s7G3ErS-ruCXgDFFwY8HyHQijfA',
                          first_item_number=1,
                          last_item_number=2))
    file_ready = False
    while not file_ready:
        data = client.get('/get_playlist_downloading_progress').get_json()
        if data['Status_code'] == 3:
            time.sleep(1)
            pass
        elif data['Status_code'] == 4:
            sep = os.path.sep
            dir = f'{TEMP_DIR}{sep}Task1{sep}'
            assert os.path.isfile(dir + os.listdir(dir)[0]) is True
            file_ready = True
        else:
            raise Exception('Unexpected task status code')


def test_sign_up_view(client):
    r = client.get('/sign_up')
    assert r.status_code == 200

    r = client.post('/sign_up', data=dict(username='user',
                                          email='user@example.com',
                                          password='12345678',
                                          repeat_password='12345678'))
    assert b'Username is already taken, please use a different username.' in r.data

    r = client.post('/sign_up', data=dict(username='user2',
                                          email='user2@example.com',
                                          password='12345678',
                                          repeat_password='12345678'))
    assert b'User successfully created.' in r.data

    r = client.post('/sign_up', data=dict(username='us3',
                                          email='user3@example.com',
                                          password='12345678',
                                          repeat_password='12345678'))
    assert b'Username must be at least 4 symbols long.' in r.data

    r = client.post('/sign_up', data=dict(username='user3',
                                          email='user@example.com',
                                          password='12345678',
                                          repeat_password='12345678'))
    assert b'Email address is already taken, please use a different email.' in r.data

    r = client.post('/sign_up', data=dict(username='user3',
                                          email='user3@example.com',
                                          password='1234567',
                                          repeat_password='12345678'))
    assert b'Password must be at least 8 symbols long.' in r.data

    users = User.query.all()

    assert len(users) == 2


def test_sign_in_view(client):
    r = client.get('/sign_in')
    assert r.status_code == 200

    r = client.post('/sign_in', data=dict(username='user',
                                          email='user@example.com',
                                          password='12345678'))
    assert b'Please confirm email and then you can sign in.' in r.data

    u = User.query.get(1)
    u.confirmed = True
    db.session.add(u)
    db.session.commit()

    r = client.post('/sign_in', data=dict(username='user',
                                          email='user@example.com',
                                          password='12345678'),
                    follow_redirects=True)
    assert b'User' in r.data

    r = client.post('/sign_in', data=dict(username='user2',
                                          email='user@example.com',
                                          password='12345678'))
    assert b'Username or password is invalid.' in r.data


def test_logout_view(client):
    u = User.query.get(1)
    u.confirmed = True
    db.session.add(u)
    db.session.commit()

    r = client.post('/sign_in', data=dict(username='user',
                                          email='user@example.com',
                                          password='12345678'),
                    follow_redirects=True)
    assert b'User' in r.data

    r = client.get('/logout')
    assert b'User' not in r.data


def test_confirm_user_view(client):
    u = User.query.get(1)
    token = u.get_confirmation_token()

    r = client.get(f'/confirm_user{token}', follow_redirects=True)
    assert b'Your email confirmed, please sign in.' in r.data

    r = client.get(f'/confirm_user{token}', follow_redirects=True)
    assert b'Your email already confirmed!' in r.data

    r = client.get(f'/confirm_user{token[1:]}')
    assert r.status_code == 404


def test_request_password_change_view(client):
    u = User.query.get(1)
    u.confirmed = True
    db.session.add(u)
    db.session.commit()

    r = client.post('/sign_in', data=dict(username='user',
                                          email='user@example.com',
                                          password='12345678'),
                    follow_redirects=True)
    assert b'User' in r.data

    r = client.post('/request_password_change', data=dict(email='user@example.com'))
    assert r.status_code == 400

    r = client.get('/request_password_change')
    assert b'Please check your email to continue process.' in r.data

    r = client.get('/logout')
    assert b'User' not in r.data

    r = client.get('/request_password_change')
    assert b'Please enter your email.' in r.data

    r = client.post('/request_password_change', data=dict(email='user@example.co'))
    assert b'<-- Failed to find user with this email.' in r.data

    r = client.post('/request_password_change', data=dict(email='user@example.com'))
    assert b'Please check your email to continue process.' in r.data


def test_change_password_view(client):
    u = User.query.get(1)
    token = u.get_confirmation_token()

    r = client.get(f'/change_password{token}')
    assert r.status_code == 200

    r = client.get(f'/change_password{token[1:]}')
    assert r.status_code == 404

    r = client.post(f'/change_password{token}', data=dict(password='password', repeat_password='password'),
                    follow_redirects=True)
    assert b'Your password successfully changed!' in r.data
    assert u.check_password('password') is True
